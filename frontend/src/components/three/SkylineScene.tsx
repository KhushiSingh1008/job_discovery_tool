/**
 * Hero scene: an isometric "skyline" of rounded blocks, one per listing slot, that grows
 * in on load, turns slowly and leans towards the pointer. Loaded lazily (three.js chunk).
 */
import { ContactShadows, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group } from "three";
import { MathUtils } from "three";

import { SCENE_COLORS } from "./palette";

const GRID = 5;
const SPACING = 1.12;
const BLOCK = 0.86;
const GROW_SECONDS = 1.1;
const STAGGER_SECONDS = 0.045;

interface Block {
  x: number;
  z: number;
  height: number;
  color: string;
  delay: number;
}

/** Deterministic pseudo-random numbers so the skyline looks the same on every visit. */
function seeded(seed: number) {
  let state = seed;
  return () => {
    state = (state * 16807) % 2147483647;
    return (state - 1) / 2147483646;
  };
}

function buildBlocks(): Block[] {
  const random = seeded(7);
  const offset = ((GRID - 1) * SPACING) / 2;
  const blocks: Block[] = [];
  for (let i = 0; i < GRID; i++) {
    for (let j = 0; j < GRID; j++) {
      const distance = Math.hypot(i - (GRID - 1) / 2, j - (GRID - 1) / 2);
      const height = 0.35 + random() * 1.6 + (2.6 - distance) * 0.35;
      const roll = random();
      const color =
        roll > 0.86
          ? SCENE_COLORS.bronze
          : roll > 0.55
            ? SCENE_COLORS.paper
            : roll > 0.25
              ? SCENE_COLORS.slate
              : SCENE_COLORS.ink;
      blocks.push({
        x: i * SPACING - offset,
        z: j * SPACING - offset,
        height: Math.max(0.3, height),
        color,
        delay: (i + j) * STAGGER_SECONDS,
      });
    }
  }
  return blocks;
}

function GrowingBlock({ block, animate }: { block: Block; animate: boolean }) {
  const group = useRef<Group>(null);
  useFrame(({ clock }) => {
    if (!group.current) return;
    const t = animate ? (clock.elapsedTime - block.delay) / GROW_SECONDS : 1;
    const eased = 1 - Math.pow(1 - MathUtils.clamp(t, 0, 1), 3);
    group.current.scale.y = Math.max(0.001, eased);
  });
  return (
    <group ref={group} position={[block.x, 0, block.z]}>
      <RoundedBox
        args={[BLOCK, block.height, BLOCK]}
        radius={0.07}
        smoothness={3}
        position={[0, block.height / 2, 0]}
        castShadow
      >
        <meshStandardMaterial color={block.color} roughness={0.72} metalness={0.05} />
      </RoundedBox>
    </group>
  );
}

// Deterministic, so it is computed once for the module rather than per render.
const BLOCKS = buildBlocks();

function Skyline({ animate }: { animate: boolean }) {
  const group = useRef<Group>(null);

  useFrame(({ pointer }, delta) => {
    if (!group.current || !animate) return;
    group.current.rotation.y += delta * 0.06;
    group.current.rotation.x = MathUtils.lerp(group.current.rotation.x, -pointer.y * 0.08, 0.05);
    group.current.position.y = MathUtils.lerp(group.current.position.y, pointer.x * 0.1, 0.05);
  });

  return (
    <group ref={group} rotation={[0, Math.PI / 4, 0]}>
      {BLOCKS.map((block) => (
        <GrowingBlock key={`${block.x}:${block.z}`} block={block} animate={animate} />
      ))}
    </group>
  );
}

export interface SceneProps {
  animate: boolean;
}

export default function SkylineScene({ animate }: SceneProps) {
  return (
    <Canvas
      camera={{ position: [7.5, 6.2, 7.5], fov: 30 }}
      dpr={[1, 2]}
      shadows
      frameloop={animate ? "always" : "demand"}
      gl={{ antialias: true, alpha: true }}
      aria-hidden="true"
      onCreated={({ camera }) => camera.lookAt(0, 0.9, 0)}
    >
      <hemisphereLight args={[SCENE_COLORS.paper, SCENE_COLORS.ink, 0.9]} />
      <directionalLight
        position={[5, 9, 3]}
        intensity={2.1}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-6, 3, -4]} intensity={0.45} color={SCENE_COLORS.bronze} />
      <Skyline animate={animate} />
      <ContactShadows position={[0, -0.01, 0]} opacity={0.35} scale={12} blur={2.6} far={4} />
    </Canvas>
  );
}
