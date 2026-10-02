import { animate, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

import styles from "./Match.module.css";

const RADIUS = 52;

function toneFor(score: number) {
  if (score >= 70) return "var(--color-good)";
  if (score >= 45) return "var(--color-warn)";
  return "var(--color-bad)";
}

/** Circular score that draws itself and counts up. */
export function ScoreDial({ score }: { score: number }) {
  const reducedMotion = useReducedMotion() ?? false;
  const [counted, setCounted] = useState(0);
  const shown = reducedMotion ? score : counted;

  useEffect(() => {
    if (reducedMotion) return;
    const controls = animate(0, score, {
      duration: 0.9,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (value) => setCounted(Math.round(value)),
    });
    return () => controls.stop();
  }, [score, reducedMotion]);

  return (
    <div className={styles.dial} role="img" aria-label={`Match score ${score} out of 100`}>
      <svg viewBox="0 0 120 120">
        <circle className={styles.dialTrack} cx="60" cy="60" r={RADIUS} />
        <motion.circle
          className={styles.dialValue}
          cx="60"
          cy="60"
          r={RADIUS}
          stroke={toneFor(score)}
          initial={{ pathLength: reducedMotion ? score / 100 : 0 }}
          animate={{ pathLength: score / 100 }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <span className={styles.dialNumber} aria-hidden="true">
        {shown}
      </span>
    </div>
  );
}
