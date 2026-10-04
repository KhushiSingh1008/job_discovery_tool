import { motion } from "motion/react";

import type { MatchResult } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Tag } from "../../components/ui/Chip";
import { useCopyToClipboard } from "../../hooks/useCopyToClipboard";
import { ScoreDial } from "./ScoreDial";
import styles from "./Match.module.css";

function Suggestion({ text }: { text: string }) {
  const { copied, copy } = useCopyToClipboard();
  return (
    <li className={styles.suggestion}>
      <p>{text}</p>
      <Button size="sm" variant="ghost" onClick={() => void copy(text)}>
        {copied ? "Copied" : "Copy"}
      </Button>
    </li>
  );
}

function SkillList({
  title,
  skills,
  tone,
  empty,
}: {
  title: string;
  skills: string[];
  tone: "good" | "outline";
  empty: string;
}) {
  return (
    <div>
      <h3>{title}</h3>
      {skills.length ? (
        <ul className={styles.chipList}>
          {skills.map((skill) => (
            <li key={skill}>
              <Tag tone={tone}>{skill}</Tag>
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.muted}>{empty}</p>
      )}
    </div>
  );
}

interface MatchResultViewProps {
  result: MatchResult;
  /** Hidden where line-by-line resume edits are shown instead. */
  showSuggestions?: boolean;
}

export function MatchResultView({ result, showSuggestions = true }: MatchResultViewProps) {
  return (
    <motion.section
      className={styles.result}
      aria-labelledby="match-result-heading"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className={styles.resultHead}>
        <ScoreDial score={result.score} />
        <div className={styles.resultSummary}>
          <h2 id="match-result-heading">How well you fit</h2>
          <p>{result.summary}</p>
          <Tag tone={result.engine === "claude" ? "accent" : "neutral"}>
            {result.engine === "claude" ? "AI analysis" : "Keyword match (offline)"}
          </Tag>
          {result.notice && <p className={styles.notice}>{result.notice}</p>}
        </div>
      </div>

      <div className={styles.skills}>
        <SkillList
          title="You already show"
          skills={result.matched_skills}
          tone="good"
          empty="No clear overlap yet."
        />
        <SkillList
          title="Missing or not evidenced"
          skills={result.missing_skills}
          tone="outline"
          empty="Nothing important missing."
        />
      </div>

      {showSuggestions && result.suggestions.length > 0 && (
        <div>
          <h3>Bullet points to try</h3>
          <ol className={styles.suggestions}>
            {result.suggestions.map((text) => (
              <Suggestion key={text} text={text} />
            ))}
          </ol>
        </div>
      )}
    </motion.section>
  );
}
