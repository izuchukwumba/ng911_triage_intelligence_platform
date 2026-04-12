import { randomUUID } from 'crypto';
import type { IncidentRecord, IncidentDomain } from '@ng911/incident-schema';
import { SCHEMA_VERSION } from '@ng911/incident-schema';
import { validateLocation } from '@ng911/location-validator';
import {
  DOMAIN_KEYWORDS,
  DOMAIN_KEYWORDS_ES,
  SEVERITY_INDICATOR_KEYWORDS,
  SEVERITY_INDICATOR_KEYWORDS_ES,
  SUBTYPE_MAP,
} from './keywords';
import { extractAddress } from './address-extractor';
import { estimateConfidence } from './confidence';
import { filterNegatedIndicators } from './negation';
import { detectLanguage } from './language-detection';
import { detectCallerStress } from './stress-detector';

export const PARSER_VERSION = '0.2.0';

// ---------------------------------------------------------------------------
// Domain classification
// ---------------------------------------------------------------------------

function classifyDomain(
  text: string,
  lang: string,
): { domain: IncidentDomain; confidence: number } {
  const lower = text.toLowerCase();

  const scores = Object.fromEntries(
    Object.keys(DOMAIN_KEYWORDS).map((d) => [d, 0]),
  ) as Record<IncidentDomain, number>;

  // Score English keywords
  for (const [domain, keywords] of Object.entries(DOMAIN_KEYWORDS) as [IncidentDomain, string[]][]) {
    for (const kw of keywords) {
      if (lower.includes(kw)) scores[domain]++;
    }
  }

  // Supplement with Spanish keywords when detected
  if (lang === 'es') {
    for (const [domain, keywords] of Object.entries(DOMAIN_KEYWORDS_ES) as [IncidentDomain, string[]][]) {
      for (const kw of keywords) {
        if (lower.includes(kw)) scores[domain]++;
      }
    }
  }

  // Hazmat signals should not double-count as fire
  if (scores.hazmat > 0) scores.fire = Math.max(0, scores.fire - scores.hazmat);

  const ranked = (Object.entries(scores) as [IncidentDomain, number][])
    .filter(([d]) => d !== 'other' && d !== 'unknown')
    .sort(([, a], [, b]) => b - a);

  const [topDomain, topScore] = ranked[0];

  if (topScore === 0) return { domain: 'unknown', confidence: 0.10 };

  const total = ranked.reduce((acc, [, v]) => acc + v, 0);
  const rawConfidence = total > 0 ? topScore / total : 0;

  // Calibrate: single hit → ~0.50, dominant hits → up to ~0.90
  const confidence = Math.min(0.90, 0.40 + rawConfidence * 0.55);

  return { domain: topDomain, confidence };
}

// ---------------------------------------------------------------------------
// Subtype classification
// ---------------------------------------------------------------------------

function classifySubtype(domain: IncidentDomain, text: string): string {
  const lower = text.toLowerCase();
  const subtypes = SUBTYPE_MAP[domain] ?? {};

  for (const [subtype, keywords] of Object.entries(subtypes)) {
    if (keywords.some((kw) => lower.includes(kw))) return subtype;
  }

  return 'unclassified';
}

// ---------------------------------------------------------------------------
// Severity indicator extraction  (with negation filtering)
// ---------------------------------------------------------------------------

function extractSeverityIndicators(text: string, lang: string): string[] {
  const lower = text.toLowerCase();
  const rawFound: string[] = [];

  // English indicators
  for (const indicator of Object.keys(SEVERITY_INDICATOR_KEYWORDS)) {
    const keywords = SEVERITY_INDICATOR_KEYWORDS[indicator] ?? [];
    if (keywords.some((kw) => lower.includes(kw))) {
      rawFound.push(indicator);
    }
  }

  // Spanish indicators — merge without duplicates
  if (lang === 'es') {
    for (const indicator of Object.keys(SEVERITY_INDICATOR_KEYWORDS_ES)) {
      if (rawFound.includes(indicator)) continue;
      const keywords = SEVERITY_INDICATOR_KEYWORDS_ES[indicator] ?? [];
      if (keywords.some((kw) => lower.includes(kw))) {
        rawFound.push(indicator);
      }
    }
  }

  // Build combined keyword map for negation checking
  const combinedKws: Record<string, string[]> = {};
  for (const [k, v] of Object.entries(SEVERITY_INDICATOR_KEYWORDS)) {
    combinedKws[k] = [...(combinedKws[k] ?? []), ...v];
  }
  if (lang === 'es') {
    for (const [k, v] of Object.entries(SEVERITY_INDICATOR_KEYWORDS_ES)) {
      combinedKws[k] = [...(combinedKws[k] ?? []), ...v];
    }
  }

  // Filter out negated indicators
  return filterNegatedIndicators(lower, rawFound, combinedKws);
}

// ---------------------------------------------------------------------------
// Victim count estimation
// ---------------------------------------------------------------------------

function estimateVictimCount(text: string): number | null {
  // Explicit numeric count: "3 people hurt", "two victims"
  const numericMatch = text.match(/(\d+)\s+(?:people|persons?|victims?|individuals?)\s+(?:hurt|injured|shot|dead|down)/i);
  if (numericMatch) return parseInt(numericMatch[1], 10);

  // Spanish: "hay 2 heridos", "3 personas heridas"
  const esMatch = text.match(/(\d+)\s+(?:personas?|víctimas?|heridos?)/i);
  if (esMatch) return parseInt(esMatch[1], 10);

  // Indefinite plurals
  if (/\b(?:multiple|several|many|crowd of|varias|múltiples|varios)\s+(?:people|victims|persons?|personas?|víctimas?)/i.test(text)) {
    return null;
  }

  return 1;
}

// ---------------------------------------------------------------------------
// Summary generation
// ---------------------------------------------------------------------------

const DOMAIN_LABELS: Record<IncidentDomain, string> = {
  police: 'Police',
  fire: 'Fire',
  ems: 'Medical',
  hazmat: 'Hazmat',
  other: 'Emergency',
  unknown: 'Unknown',
};

function generateSummary(
  domain: IncidentDomain,
  subtype: string,
  indicators: string[],
  addressText: string | null,
): string {
  const domainLabel = DOMAIN_LABELS[domain];
  const subtypeLabel =
    subtype === 'unclassified' ? null : subtype.replace(/_/g, ' ');

  let summary = subtypeLabel
    ? `Reported ${subtypeLabel}`
    : `${domainLabel} incident`;

  const criticalIndicators = indicators.filter((i) =>
    ['active_bleeding', 'not_breathing', 'unconscious', 'weapon_present', 'active_violence', 'cardiac_event'].includes(i),
  );

  if (criticalIndicators.length > 0) {
    const labels = criticalIndicators
      .slice(0, 3)
      .map((i) => i.replace(/_/g, ' '));
    summary += ` with ${labels.join(', ')}`;
  }

  if (addressText) {
    summary += ` at ${addressText}`;
  }

  return summary.charAt(0).toUpperCase() + summary.slice(1);
}

// ---------------------------------------------------------------------------
// Main parser entry point
// ---------------------------------------------------------------------------

export function parseTranscript(text: string): IncidentRecord {
  const normalized = text.trim();
  const now = new Date().toISOString();

  // Language detection first — informs keyword selection
  const lang = detectLanguage(normalized);

  const { domain, confidence: domainConfidence } = classifyDomain(normalized, lang);
  const subtype = classifySubtype(domain, normalized);

  // Severity extraction with negation filtering
  const severityIndicators = extractSeverityIndicators(normalized, lang);

  const victimCount = estimateVictimCount(normalized);
  const addressText = extractAddress(normalized);
  const callerStress = detectCallerStress(normalized);

  const locationValidation = validateLocation({
    address_text: addressText,
    lat: null,
    lng: null,
  });

  const overallConfidence = estimateConfidence(
    domainConfidence,
    severityIndicators,
    addressText,
  );

  const summary = generateSummary(domain, subtype, severityIndicators, addressText);

  return {
    incident_id: randomUUID(),
    received_at: now,
    source_type: 'transcript',
    raw_input: { text: normalized },
    incident: {
      domain,
      subtype,
      summary,
      severity_indicators: severityIndicators,
      victim_count_estimate: victimCount,
      confidence: Math.round(overallConfidence * 1000) / 1000,
    },
    location: {
      address_text: addressText,
      lat: null,
      lng: null,
      ...locationValidation,
    },
    caller_context: {
      caller_id_hash: null,
      language_hint: lang === 'unknown' ? 'en' : lang,
      background_noise_level: null,
      caller_stress_level: callerStress,
    },
    triage: {
      priority_score: null,
      priority_tier: null,
      reason_codes: [],
    },
    audit: {
      schema_version: SCHEMA_VERSION,
      parser_version: PARSER_VERSION,
      scoring_version: null,
      processed_at: now,
    },
  };
}
