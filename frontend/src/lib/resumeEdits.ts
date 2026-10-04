/** Apply the resume edits a student accepted, leaving everything else untouched. */
import type { ResumeSuggestion } from "../api/types";

export type Decision = "accepted" | "rejected";
export type Decisions = Readonly<Record<string, Decision>>;

export interface EditedResume {
  text: string;
  /** Accepted rewrites whose quoted text was no longer found. */
  skipped: string[];
}

function lastContentLine(lines: string[]): number {
  for (let i = lines.length - 1; i >= 0; i--) if (lines[i]!.trim()) return i;
  return -1;
}

/**
 * Rewrites replace the first line containing the quoted text; additions go after the line
 * that contained their anchor in the *original* resume, so the order in which suggestions
 * are accepted never changes the result.
 */
export function applySuggestions(
  resume: string,
  suggestions: readonly ResumeSuggestion[],
  decisions: Decisions,
): EditedResume {
  const accepted = suggestions.filter((s) => decisions[s.id] === "accepted");
  const original = resume.split("\n");
  const lines = [...original];
  const skipped: string[] = [];

  for (const edit of accepted) {
    if (edit.kind !== "rewrite") continue;
    const index = lines.findIndex((line) => line.includes(edit.original));
    if (index === -1) {
      skipped.push(edit.id);
      continue;
    }
    lines[index] = lines[index]!.replace(edit.original, () => edit.replacement);
  }

  const atTop: string[] = [];
  const after = new Map<number, string[]>();
  for (const edit of accepted) {
    if (edit.kind !== "add") continue;
    let index = edit.original ? original.findIndex((line) => line.includes(edit.original)) : -1;
    if (edit.original && index === -1) index = lastContentLine(original);
    if (index === -1) atTop.push(edit.replacement);
    else after.set(index, [...(after.get(index) ?? []), edit.replacement]);
  }

  const text = [...atTop, ...lines.flatMap((line, i) => [line, ...(after.get(i) ?? [])])].join(
    "\n",
  );
  return { text, skipped };
}

export function countDecisions(suggestions: readonly ResumeSuggestion[], decisions: Decisions) {
  const accepted = suggestions.filter((s) => decisions[s.id] === "accepted").length;
  const rejected = suggestions.filter((s) => decisions[s.id] === "rejected").length;
  return { accepted, rejected, pending: suggestions.length - accepted - rejected };
}
