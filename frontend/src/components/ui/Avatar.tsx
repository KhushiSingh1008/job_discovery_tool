import styles from "./Avatar.module.css";

const TONES = ["navy", "indigo", "teal"] as const;

/** Stable colour per name, so an employer always gets the same tile. */
function toneFor(name: string) {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return TONES[hash % TONES.length]!;
}

const MINOR_WORDS = new Set(["of", "the", "and", "for", "at", "in", "ltd", "plc", "llc"]);

function initials(name: string) {
  const words = name
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter((word) => word && !MINOR_WORDS.has(word.toLowerCase()));
  return (
    words.length > 1 ? words[0]![0]! + words[1]![0]! : (words[0] ?? "?").slice(0, 2)
  ).toUpperCase();
}

/** A lettered tile standing in for an employer logo (scraped pages rarely give one). */
export function Avatar({ name, size = "md" }: { name: string; size?: "md" | "lg" }) {
  return (
    <span
      className={`${styles.avatar} ${styles[toneFor(name)]} ${styles[size]}`}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}
