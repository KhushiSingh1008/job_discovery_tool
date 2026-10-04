import { motion } from "motion/react";

import type { TrustFlag } from "../../api/types";
import styles from "./JobDetail.module.css";

const MAX_IMPACT = 35;

/** Each trust signal with its effect on the score, concerns first. */
export function TrustBreakdown({ flags }: { flags: TrustFlag[] }) {
  const sorted = [...flags].sort((a, b) => a.impact - b.impact);
  return (
    <ul className={styles.flags}>
      {sorted.map((flag, index) => {
        const tone = flag.impact > 0 ? "good" : flag.impact < 0 ? "bad" : "neutral";
        const width = `${(Math.min(Math.abs(flag.impact), MAX_IMPACT) / MAX_IMPACT) * 100}%`;
        return (
          <motion.li
            key={flag.code}
            className={`${styles.flag} ${styles[tone]}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + index * 0.05 }}
          >
            <span className={styles.impact}>
              {flag.impact > 0 ? `+${flag.impact}` : flag.impact === 0 ? "±0" : flag.impact}
            </span>
            <span className={styles.flagText}>{flag.message}</span>
            <span className={styles.bar} aria-hidden="true">
              <motion.span
                initial={{ width: 0 }}
                animate={{ width }}
                transition={{ delay: 0.2 + index * 0.05, duration: 0.5 }}
              />
            </span>
          </motion.li>
        );
      })}
    </ul>
  );
}
