// ---------------------------------------------------------------------------
// Negation Handling
//
// Problem: a keyword-only scanner misfires on phrases like:
//   "he is NOT having a heart attack"   → should not trigger cardiac_event
//   "she is NOT bleeding"               → should not trigger active_bleeding
//   "there is no gun"                   → should not trigger weapon_present
//
// Strategy: for each keyword occurrence, check whether a negation word
// appears within a short window preceding it (same sentence, ≤ 8 words back).
// If every occurrence of a keyword is negated, the indicator is suppressed.
// ---------------------------------------------------------------------------

const NEGATION_WORDS = new Set([
  'not', 'no', "isn't", "aren't", "wasn't", "weren't",
  "doesn't", "don't", "didn't", "haven't", "hasn't", "hadn't",
  "won't", "wouldn't", "can't", "cannot", "couldn't",
  "needn't", 'never', 'without', 'denies', 'deny', 'denied',
  'negative',
]);

// Multi-token cues. Tokens are compared one at a time, so phrases cannot live
// in NEGATION_WORDS — they are matched as token sequences in isNegated().
const NEGATION_PHRASES: string[][] = [
  ['ruled', 'out'],
  ['no', 'sign', 'of'],
  ['no', 'evidence', 'of'],
];

// Sentence boundary — negation scope does not cross these
const SENTENCE_BOUNDARY = /[.!?;]/;

/**
 * Tokenise text into words, preserving original positions as [start, end] spans.
 */
function tokenise(text: string): Array<{ word: string; start: number; end: number }> {
  const tokens: Array<{ word: string; start: number; end: number }> = [];
  const re = /\S+/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    tokens.push({ word: m[0].toLowerCase().replace(/[^\w']/g, ''), start: m.index, end: m.index + m[0].length });
  }
  return tokens;
}

/**
 * Returns true if a NEGATION_PHRASES entry starts at token `start` and ends
 * before the keyword token.
 */
function startsNegationPhrase(
  tokens: ReturnType<typeof tokenise>,
  start: number,
  keywordTokenIndex: number,
): boolean {
  return NEGATION_PHRASES.some(
    (phrase) =>
      start + phrase.length <= keywordTokenIndex &&
      phrase.every((word, offset) => tokens[start + offset]?.word === word),
  );
}

/**
 * Returns true if the keyword phrase (already found at `keywordStart`) is
 * negated — i.e., a negation word appears within the preceding 8 tokens
 * in the same sentence.
 */
function isNegated(
  tokens: ReturnType<typeof tokenise>,
  keywordTokenIndex: number,
  originalText: string,
): boolean {
  const windowStart = Math.max(0, keywordTokenIndex - 8);

  for (let i = keywordTokenIndex - 1; i >= windowStart; i--) {
    const tok = tokens[i];
    if (!tok) break;

    // Don't cross sentence boundaries
    const between = originalText.slice(tok.end, tokens[keywordTokenIndex]?.start ?? tok.end);
    if (SENTENCE_BOUNDARY.test(between)) break;

    if (NEGATION_WORDS.has(tok.word)) return true;
    if (startsNegationPhrase(tokens, i, keywordTokenIndex)) return true;
  }

  return false;
}

/**
 * Given the full text and extracted indicators (from keyword matching),
 * re-examine each indicator and remove those whose keywords are all negated.
 *
 * @param text          - Original (lowercased) transcript text
 * @param indicators    - List of indicator keys to check
 * @param indicatorKws  - Map of indicator key → keyword list
 */
export function filterNegatedIndicators(
  text: string,
  indicators: string[],
  indicatorKws: Record<string, string[]>,
): string[] {
  const lower = text.toLowerCase();
  const tokens = tokenise(lower);

  return indicators.filter((indicator) => {
    const keywords = indicatorKws[indicator] ?? [];

    // Check each keyword; if ANY occurrence is non-negated, keep the indicator
    for (const kw of keywords) {
      const kwLower = kw.toLowerCase();
      let searchFrom = 0;

      while (true) {
        const idx = lower.indexOf(kwLower, searchFrom);
        if (idx === -1) break;

        // Find the token index that starts at or after idx
        const kwTokenIdx = tokens.findIndex((t) => t.start >= idx);
        if (kwTokenIdx === -1) break;

        if (!isNegated(tokens, kwTokenIdx, lower)) {
          return true; // at least one non-negated hit — keep indicator
        }

        searchFrom = idx + 1;
      }
    }

    return false; // all occurrences were negated — drop indicator
  });
}
