/** Word-level diff, so a suggestion can highlight just the words it changes. */

export type DiffPart = { type: "same" | "removed" | "added"; text: string };

/** Above this many token pairs the table gets slow; fall back to whole-text replace. */
const MAX_CELLS = 40_000;

/** Words, whitespace runs and punctuation, so “till” → “till,” only marks the comma. */
const tokenize = (text: string) => text.match(/\s+|[.,;:!?()]|[^\s.,;:!?()]+/g) ?? [];

function merge(parts: DiffPart[]): DiffPart[] {
  const merged: DiffPart[] = [];
  for (const part of parts) {
    const last = merged.at(-1);
    if (last && last.type === part.type) last.text += part.text;
    else merged.push({ ...part });
  }
  return merged;
}

/** Longest-common-subsequence diff over words (whitespace kept as its own tokens). */
export function wordDiff(before: string, after: string): DiffPart[] {
  const a = tokenize(before);
  const b = tokenize(after);
  if (a.length * b.length > MAX_CELLS) {
    return merge([
      { type: "removed", text: before },
      { type: "added", text: after },
    ]).filter((part) => part.text);
  }

  // lcs[i][j] = length of the common subsequence of a[i:] and b[j:]
  const lcs = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i]![j] =
        a[i] === b[j] ? lcs[i + 1]![j + 1]! + 1 : Math.max(lcs[i + 1]![j]!, lcs[i]![j + 1]!);
    }
  }

  const parts: DiffPart[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      parts.push({ type: "same", text: a[i]! });
      i++;
      j++;
    } else if (lcs[i + 1]![j]! >= lcs[i]![j + 1]!) {
      parts.push({ type: "removed", text: a[i++]! });
    } else {
      parts.push({ type: "added", text: b[j++]! });
    }
  }
  while (i < a.length) parts.push({ type: "removed", text: a[i++]! });
  while (j < b.length) parts.push({ type: "added", text: b[j++]! });
  return merge(parts);
}
