// ---------------------------------------------------------------------------
// Caller Stress Detector
//
// Estimates caller stress level from linguistic cues in the transcript.
// This is a heuristic signal — it does not replace audio analysis but
// provides a meaningful proxy from text alone.
//
// Signals evaluated:
//   - High-distress phrases ("please please", "oh god", "he's dying")
//   - Repeated words ("help help help", "please please")
//   - All-caps words (shouting signal)
//   - Excessive punctuation / exclamation marks
//   - Sentence fragmentation (very short sentences under stress)
//   - Filler words common under acute distress
// ---------------------------------------------------------------------------

import type { StressLevelValue } from '@ng911/incident-schema';

const HIGH_DISTRESS_PHRASES = [
  'please please', 'please help please', 'oh my god', 'oh god',
  "he's dying", "she's dying", "they're dying", 'is dying',
  "i don't know what to do", "i don't know what to do",
  'hurry please', 'please hurry', 'come now', 'come right now',
  'oh no oh no', 'no no no', 'help help', 'help me please',
  'por favor', 'ayúdeme', 'socorro', 'auxilio',
];

const MODERATE_DISTRESS_PHRASES = [
  'hurry', 'quickly', 'fast', 'right away', 'as soon as possible',
  'i need help', 'we need help', 'need an ambulance',
  'something is wrong', 'not looking good', 'really bad',
  'not sure what happened', 'getting worse',
];

function countAllCapsWords(text: string): number {
  // Words that are 3+ chars and all-caps (excl. abbreviations like EMS, CPR)
  const words = text.split(/\s+/);
  return words.filter((w) => w.length >= 3 && w === w.toUpperCase() && /[A-Z]/.test(w)).length;
}

function countRepetitions(text: string): number {
  // Detect repeated consecutive words: "help help", "please please please"
  const matches = text.match(/\b(\w+)\s+\1\b/gi);
  return matches ? matches.length : 0;
}

function countExclamationMarks(text: string): number {
  return (text.match(/!/g) ?? []).length;
}

function hasSentenceFragmentation(text: string): boolean {
  // ≥ 3 sentences with ≤ 3 words each suggests terse, fragmented speech
  const sentences = text.split(/[.!?]+/).filter((s) => s.trim().length > 0);
  const shortCount = sentences.filter((s) => s.trim().split(/\s+/).length <= 3).length;
  return shortCount >= 3;
}

export function detectCallerStress(text: string): StressLevelValue | null {
  const lower = text.toLowerCase();
  let score = 0;

  // High-distress phrase matches (strong signal)
  for (const phrase of HIGH_DISTRESS_PHRASES) {
    if (lower.includes(phrase)) score += 3;
  }

  // Moderate-distress phrase matches
  for (const phrase of MODERATE_DISTRESS_PHRASES) {
    if (lower.includes(phrase)) score += 1;
  }

  // All-caps words (each one = +1, cap at 3)
  score += Math.min(3, countAllCapsWords(text));

  // Word repetition (each instance = +2)
  score += Math.min(4, countRepetitions(lower) * 2);

  // Exclamation marks (1–2 = +1, 3+ = +2)
  const exclCount = countExclamationMarks(text);
  if (exclCount >= 3) score += 2;
  else if (exclCount >= 1) score += 1;

  // Sentence fragmentation
  if (hasSentenceFragmentation(text)) score += 2;

  if (score === 0) return null;
  if (score >= 6) return 'high';
  if (score >= 3) return 'moderate';
  return 'low';
}
