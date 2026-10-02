/**
 * Safe entry points for the 3D scenes.
 *
 * three.js is code-split (React.lazy) so it never blocks first paint. A scene only renders
 * when WebGL works; otherwise, or if it throws, a static fallback with the same meaning is
 * shown. Scenes stop animating when off-screen or when the user prefers reduced motion.
 */
import { useInView, useReducedMotion } from "motion/react";
import { lazy, Suspense, useRef, type ReactNode } from "react";

import { useWebGL } from "../../hooks/useWebGL";
import { ErrorBoundary } from "../ErrorBoundary";
import styles from "./Scenes.module.css";
import type { HoursRingSceneProps } from "./HoursRingScene";

const SkylineScene = lazy(() => import("./SkylineScene"));
const HoursRingScene = lazy(() => import("./HoursRingScene"));

function SceneFrame({
  className,
  fallback,
  render,
}: {
  className: string;
  fallback: ReactNode;
  render: (animate: boolean) => ReactNode;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const inView = useInView(frame, { margin: "120px" });
  const reducedMotion = useReducedMotion() ?? false;
  const webgl = useWebGL();
  const animate = inView && !reducedMotion;

  return (
    <div ref={frame} className={className}>
      {webgl ? (
        <ErrorBoundary fallback={fallback}>
          <Suspense fallback={fallback}>{render(animate)}</Suspense>
        </ErrorBoundary>
      ) : (
        fallback
      )}
    </div>
  );
}

function SkylineFallback() {
  // Isometric bars drawn in SVG: the same idea as the 3D scene, no WebGL required.
  const bars = [44, 70, 56, 92, 62, 80, 38];
  return (
    <svg className={styles.fallback} viewBox="0 0 280 200" role="presentation">
      {bars.map((height, i) => {
        const x = 30 + i * 32;
        const y = 170 - height;
        const fill = i === 3 ? "var(--bronze)" : i % 2 ? "var(--slate)" : "var(--ink)";
        return (
          <g key={x}>
            <rect x={x} y={y} width="24" height={height} rx="3" fill={fill} />
            <rect x={x} y={y} width="24" height="6" rx="3" fill="var(--paper)" opacity="0.5" />
          </g>
        );
      })}
    </svg>
  );
}

export function SkylineHero({ className }: { className?: string }) {
  return (
    <SceneFrame
      className={`${styles.frame} ${className ?? ""}`}
      fallback={<SkylineFallback />}
      render={(animate) => <SkylineScene animate={animate} />}
    />
  );
}

const TONE_VARS: Record<HoursRingSceneProps["tone"], string> = {
  good: "var(--color-good)",
  warn: "var(--color-warn)",
  bad: "var(--color-bad)",
  bronze: "var(--color-accent)",
};

function RingFallback({ committedFraction, tone }: Omit<HoursRingSceneProps, "animate">) {
  const fill = `${Math.min(committedFraction, 1) * 100}%`;
  return (
    <div
      className={styles.ringFallback}
      style={{
        background: `conic-gradient(${TONE_VARS[tone]} ${fill}, var(--color-surface-sunken) 0)`,
      }}
    />
  );
}

export function HoursRing(props: Omit<HoursRingSceneProps, "animate"> & { className?: string }) {
  const { className, ...ring } = props;
  return (
    <SceneFrame
      className={`${styles.frame} ${className ?? ""}`}
      fallback={<RingFallback {...ring} />}
      render={(animate) => <HoursRingScene {...ring} animate={animate} />}
    />
  );
}
