/**
 * 3D gauge for weekly work hours: a tilted torus whose filled arc is the share of the visa
 * limit already committed. A faint second arc shows where pending interviews would take it.
 */
import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Group, Mesh } from "three";
import { MathUtils, TorusGeometry } from "three";

import { SCENE_COLORS } from "./palette";

const RADIUS = 1.35;
const TUBE = 0.16;
const FULL_TURN = Math.PI * 2;
const SETTLED = 0.001;

export interface HoursRingSceneProps {
  committedFraction: number; // committed hours / cap (may exceed 1)
  potentialFraction: number; // (committed + interviewing) / cap
  tone: "good" | "warn" | "bad" | "teal";
  animate: boolean;
}

function arcGeometry(fraction: number, tube: number) {
  const arc = MathUtils.clamp(fraction, 0.0001, 1) * FULL_TURN;
  return new TorusGeometry(RADIUS, tube, 24, 160, arc);
}

interface ArcProps {
  target: number;
  color: string;
  tube: number;
  animate: boolean;
  opacity?: number;
}

/**
 * An arc that eases towards ``target``. Torus arcs cannot be scaled into a different
 * length, so the geometry is rebuilt (and the old one disposed) only while it is moving.
 */
function AnimatedArc({ target, color, tube, animate, opacity = 1 }: ArcProps) {
  const mesh = useRef<Mesh>(null);
  // Animated arcs grow in from empty; static ones start at their final length.
  const [initialFraction] = useState(() => (animate ? 0 : target));
  const shown = useRef(initialFraction);
  const initialGeometry = useMemo(
    () => arcGeometry(initialFraction, tube),
    [initialFraction, tube],
  );

  useEffect(() => {
    const node = mesh.current;
    return () => node?.geometry.dispose();
  }, []);

  useFrame(() => {
    const node = mesh.current;
    if (!node || Math.abs(shown.current - target) < SETTLED) return;
    const next = animate ? MathUtils.lerp(shown.current, target, 0.08) : target;
    shown.current = Math.abs(next - target) < SETTLED ? target : next;
    node.geometry.dispose();
    node.geometry = arcGeometry(shown.current, tube);
  });

  return (
    <mesh ref={mesh} geometry={initialGeometry}>
      <meshStandardMaterial
        color={color}
        roughness={0.45}
        metalness={0.15}
        transparent={opacity < 1}
        opacity={opacity}
      />
    </mesh>
  );
}

function Track() {
  const geometry = useMemo(() => arcGeometry(1, TUBE * 0.62), []);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={SCENE_COLORS.indigo}
        roughness={0.9}
        transparent
        opacity={0.22}
      />
    </mesh>
  );
}

function Ring({ committedFraction, potentialFraction, tone, animate }: HoursRingSceneProps) {
  const group = useRef<Group>(null);

  useFrame(({ pointer, clock }) => {
    if (!group.current || !animate) return;
    const { rotation } = group.current;
    rotation.x = MathUtils.lerp(rotation.x, -0.55 - pointer.y * 0.15, 0.06);
    rotation.y = MathUtils.lerp(
      rotation.y,
      pointer.x * 0.25 + Math.sin(clock.elapsedTime * 0.6) * 0.05,
      0.06,
    );
  });

  return (
    <group ref={group} rotation={[-0.55, 0, 0]}>
      {/* Start the arcs at 12 o'clock and fill clockwise. */}
      <group rotation={[0, 0, Math.PI / 2]} scale={[1, -1, 1]}>
        <Track />
        {potentialFraction > committedFraction && (
          <AnimatedArc
            target={potentialFraction}
            color={SCENE_COLORS.teal}
            opacity={0.35}
            tube={TUBE * 0.8}
            animate={animate}
          />
        )}
        <AnimatedArc
          target={committedFraction}
          color={SCENE_COLORS[tone]}
          tube={TUBE}
          animate={animate}
        />
      </group>
    </group>
  );
}

export default function HoursRingScene(props: HoursRingSceneProps) {
  return (
    <Canvas
      camera={{ position: [0, 0, 5.2], fov: 38 }}
      dpr={[1, 2]}
      frameloop={props.animate ? "always" : "demand"}
      gl={{ antialias: true, alpha: true }}
      aria-hidden="true"
    >
      <ambientLight intensity={0.55} />
      <directionalLight position={[3, 4, 5]} intensity={2.2} />
      <directionalLight position={[-4, -2, 2]} intensity={0.5} color={SCENE_COLORS.teal} />
      <Ring {...props} />
    </Canvas>
  );
}
