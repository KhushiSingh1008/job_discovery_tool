/**
 * Where each suggested edit sits in the resume, and the resume that results from the edits
 * a student accepted. The highlighted view and the exported text share one layout, so what
 * is shown is exactly what is saved.
 */
import type { ResumeSuggestion } from "../api/types";

export type Decision = "accepted" | "rejected";
export type Decisions = Readonly<Record<string, Decision>>;

export type Segment = { kind: "text"; text: string } | { kind: "edit"; id: string };

export interface DocumentLine {
  segments: Segment[];
  /** Ids of "add" suggestions that go directly after this line. */
  additions: string[];
}

export interface ResumeLayout {
  /** Ids of "add" suggestions that go before the first line. */
  top: string[];
  lines: DocumentLine[];
  /** Rewrites whose quoted text is not in the resume (or overlaps another rewrite). */
  unplaced: string[];
}

interface Range {
  start: number;
  end: number;
  id: string;
}

function lastContentLine(lines: string[]): number {
  for (let i = lines.length - 1; i >= 0; i--) if (lines[i]!.trim()) return i;
  return -1;
}

/** A rewrite goes at the first free occurrence of its quoted text; an addition after its anchor. */
export function layoutSuggestions(
  resume: string,
  suggestions: readonly ResumeSuggestion[],
): ResumeLayout {
  const texts = resume.split("\n");
  const ranges: Range[][] = texts.map(() => []);
  const additions: string[][] = texts.map(() => []);
  const top: string[] = [];
  const unplaced: string[] = [];

  for (const edit of suggestions) {
    if (edit.kind === "add") {
      let index = edit.original ? texts.findIndex((line) => line.includes(edit.original)) : -1;
      if (edit.original && index === -1) index = lastContentLine(texts);
      if (index === -1) top.push(edit.id);
      else additions[index]!.push(edit.id);
      continue;
    }

    let placed = false;
    for (let index = 0; index < texts.length && !placed && edit.original; index++) {
      const start = texts[index]!.indexOf(edit.original);
      if (start === -1) continue;
      const end = start + edit.original.length;
      if (ranges[index]!.some((r) => start < r.end && r.start < end)) continue;
      ranges[index]!.push({ start, end, id: edit.id });
      placed = true;
    }
    if (!placed) unplaced.push(edit.id);
  }

  const lines = texts.map((text, index) => {
    const segments: Segment[] = [];
    let cursor = 0;
    for (const range of [...ranges[index]!].sort((x, y) => x.start - y.start)) {
      if (range.start > cursor)
        segments.push({ kind: "text", text: text.slice(cursor, range.start) });
      segments.push({ kind: "edit", id: range.id });
      cursor = range.end;
    }
    if (cursor < text.length || segments.length === 0) {
      segments.push({ kind: "text", text: text.slice(cursor) });
    }
    return { segments, additions: additions[index]! };
  });

  return { top, lines, unplaced };
}

export interface EditedResume {
  text: string;
  /** Accepted rewrites whose quoted text could not be found. */
  skipped: string[];
}

export function applySuggestions(
  resume: string,
  suggestions: readonly ResumeSuggestion[],
  decisions: Decisions,
): EditedResume {
  const layout = layoutSuggestions(resume, suggestions);
  const byId = new Map(suggestions.map((s) => [s.id, s]));
  const accepted = (id: string) => decisions[id] === "accepted";
  const added = (ids: string[]) => ids.filter(accepted).map((id) => byId.get(id)!.replacement);

  const lines = layout.lines.flatMap((line) => {
    const text = line.segments
      .map((segment) => {
        if (segment.kind === "text") return segment.text;
        const edit = byId.get(segment.id)!;
        return accepted(edit.id) ? edit.replacement : edit.original;
      })
      .join("");
    return [text, ...added(line.additions)];
  });

  return {
    text: [...added(layout.top), ...lines].join("\n"),
    skipped: layout.unplaced.filter(accepted),
  };
}

export function countDecisions(suggestions: readonly ResumeSuggestion[], decisions: Decisions) {
  const accepted = suggestions.filter((s) => decisions[s.id] === "accepted").length;
  const rejected = suggestions.filter((s) => decisions[s.id] === "rejected").length;
  return { accepted, rejected, pending: suggestions.length - accepted - rejected };
}
