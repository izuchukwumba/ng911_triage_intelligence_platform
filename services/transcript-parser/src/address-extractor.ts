// ---------------------------------------------------------------------------
// Address Extractor
// Attempts to pull the best available location reference from raw transcript
// text. Returns the most specific match found, or null if none detected.
// ---------------------------------------------------------------------------

const STREET_SUFFIX_ALTERNATION = [
  'street', 'st',
  'avenue', 'ave',
  'road', 'rd',
  'boulevard', 'blvd',
  'drive', 'dr',
  'lane', 'ln',
  'way',
  'court', 'ct',
  'place', 'pl',
  'circle', 'cir',
  'highway', 'hwy',
  'route', 'rt',
  'parkway', 'pkwy',
  'terrace', 'ter',
  'trail', 'trl',
  'loop',
  'alley', 'aly',
].join('|');

const ADDRESS_PATTERNS: RegExp[] = [
  // Numbered address: "123 Oak Street", "456 N Main Ave"
  new RegExp(
    `\\b(\\d+\\s+(?:[NSEW]\\.?\\s+)?[\\w]+(?:\\s+[\\w]+){0,3}\\s+(?:${STREET_SUFFIX_ALTERNATION})\\.?)\\b`,
    'i',
  ),

  // Intersection: "5th and Oak Avenue", "Main Street and Elm"
  new RegExp(
    `\\b([\\w]+(?:\\s+[\\w]+)?\\s+(?:and|&)\\s+[\\w]+(?:\\s+[\\w]+)?(?:\\s+(?:${STREET_SUFFIX_ALTERNATION}))?)\\.?\\b`,
    'i',
  ),

  // "at / near / on <street>": "near 5th street"
  new RegExp(
    `\\b(?:at|near|on)\\s+((?:\\d+\\s+)?[\\w]+(?:\\s+[\\w]+){0,3}\\s+(?:${STREET_SUFFIX_ALTERNATION})\\.?)\\b`,
    'i',
  ),
];

// Landmark pattern: "near the Riverside Hospital", "by the school"
const LANDMARK_PATTERN =
  /\b(?:near|at|by|outside|in front of)\s+((?:the\s+)?[\w\s]{3,50}?(?:park|school|hospital|mall|plaza|center|centre|station|church|clinic|parking lot|intersection))\b/i;

// Directional cross-street: "corner of Oak and Main"
const CORNER_PATTERN =
  /\b(?:corner|intersection)\s+of\s+([\w\s]+\s+and\s+[\w\s]+)/i;

export function extractAddress(text: string): string | null {
  // Try each precise pattern first
  for (const pattern of ADDRESS_PATTERNS) {
    const match = text.match(pattern);
    if (match?.[1]) {
      return match[1].trim();
    }
  }

  // Cross-street corners
  const corner = text.match(CORNER_PATTERN);
  if (corner?.[1]) return corner[1].trim();

  // Landmark fallback
  const landmark = text.match(LANDMARK_PATTERN);
  if (landmark?.[1]) return landmark[1].trim();

  return null;
}
