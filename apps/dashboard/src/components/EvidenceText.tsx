import type { ReactNode } from 'react';

export interface Highlight {
  start: number;
  end: number;
  label: string;
  // Denied or historical cues are shown struck through, not as live findings.
  muted?: boolean;
  active?: boolean;
}

interface Props {
  text: string;
  highlights: Highlight[];
}

// Renders a source transcript with evidence spans marked, so every extracted
// fact can be checked against exactly what was said.
export function EvidenceText({ text, highlights }: Props) {
  const spans = [...highlights]
    .filter((h) => h.start >= 0 && h.end <= text.length && h.end > h.start)
    .sort((a, b) => a.start - b.start);

  const parts: ReactNode[] = [];
  let cursor = 0;
  spans.forEach((h, i) => {
    if (h.start < cursor) return; // overlapping spans: keep the first
    if (h.start > cursor) parts.push(text.slice(cursor, h.start));
    parts.push(
      <mark
        key={i}
        title={h.label}
        aria-label={`${text.slice(h.start, h.end)} (${h.label})`}
        style={{
          background: h.active ? 'rgba(88,166,255,0.35)' : h.muted ? 'rgba(139,148,158,0.18)' : 'rgba(255,169,64,0.22)',
          color: 'inherit',
          textDecoration: h.muted ? 'line-through' : 'none',
          borderBottom: `2px solid ${h.muted ? 'var(--text-muted)' : 'var(--p2)'}`,
          borderRadius: '2px',
          padding: '0 1px',
        }}
      >
        {text.slice(h.start, h.end)}
      </mark>,
    );
    cursor = h.end;
  });
  if (cursor < text.length) parts.push(text.slice(cursor));

  return (
    <p style={{ fontFamily: 'var(--mono)', fontSize: '13px', lineHeight: 1.7, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
      {parts}
    </p>
  );
}
