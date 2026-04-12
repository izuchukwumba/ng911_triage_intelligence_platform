// ---------------------------------------------------------------------------
// Language Detection
//
// Lightweight heuristic language detection for English and Spanish.
// Uses high-frequency diagnostic function words unique to each language
// rather than character n-gram models, keeping the module dependency-free.
//
// Returns: 'en' | 'es' | 'unknown'
// ---------------------------------------------------------------------------

// Common Spanish function words unlikely to appear in English text
const SPANISH_MARKERS = [
  'ayuda', 'auxilio', 'ayúdeme', 'por favor', 'socorro', 'rápido',
  'está', 'están', 'estoy', 'hay', 'tiene', 'tengo', 'necesito',
  'no respira', 'no puede respirar', 'inconsciente', 'desmayó',
  'herido', 'herida', 'sangre', 'sangrado', 'dispararon', 'disparo',
  'incendio', 'fuego', 'humo', 'quemándose', 'se está quemando',
  'accidente', 'choque', 'atropelló', 'asalto', 'robo',
  'mi hijo', 'mi hija', 'mi esposo', 'mi esposa', 'mi padre', 'mi madre',
  'llamen', 'manden', 'vengan', 'necesitamos',
  'una ambulancia', 'la policía', 'los bomberos',
  'no sé', 'no sabe', 'no sabemos',
  'está muerto', 'está muriendo', 'se está muriendo',
];

// English-specific high-frequency words (for disambiguation)
const ENGLISH_MARKERS = [
  'the ', ' is ', ' are ', ' was ', ' were ', 'please', 'help', 'there',
  "i'm ", "he's ", "she's ", "it's ", "they're ", "we're ",
  'someone', 'somebody', 'something', 'happened', 'hurry',
];

export type DetectedLanguage = 'en' | 'es' | 'unknown';

export function detectLanguage(text: string): DetectedLanguage {
  const lower = text.toLowerCase();

  let esScore = 0;
  let enScore = 0;

  for (const marker of SPANISH_MARKERS) {
    if (lower.includes(marker)) esScore++;
  }

  for (const marker of ENGLISH_MARKERS) {
    if (lower.includes(marker)) enScore++;
  }

  if (esScore === 0 && enScore === 0) return 'unknown';
  if (esScore > enScore) return 'es';
  if (enScore > esScore) return 'en';

  // Tie-break: Spanish markers tend to be more specific, so trust them
  return esScore >= 2 ? 'es' : 'en';
}
