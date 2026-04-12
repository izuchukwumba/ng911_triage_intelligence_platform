import type { IncidentDomain } from '@ng911/incident-schema';
import { SCENARIO_TEMPLATES, type ScenarioTemplate } from './templates';

// ---------------------------------------------------------------------------
// Address bank — varies location specificity for evaluation coverage
// ---------------------------------------------------------------------------

const COMPLETE_ADDRESSES = [
  '742 Evergreen Terrace',
  '1600 Pennsylvania Ave NW',
  '221B Baker Street',
  '350 Fifth Avenue',
  '123 Oak Street',
  '456 Maple Avenue',
  '789 Elm Road',
  '1200 N Broad Street',
  '500 W Madison Blvd',
  '88 Lincoln Drive',
];

const PARTIAL_ADDRESSES = [
  'near 5th and Main',
  'corner of Oak and Elm',
  'somewhere on Route 9',
  'the intersection of Broadway and 42nd',
  'near the downtown library',
];

const VAGUE_ADDRESSES = [
  'near the park',
  'by the school',
  'downtown somewhere',
  'not sure of the address',
  'I think it\'s around here',
];

// ---------------------------------------------------------------------------
// Caller affect bank
// ---------------------------------------------------------------------------

const CALLER_AFFECTS = [
  'panicked', 'calm but urgent', 'crying', 'shouting',
  'whispering', 'very distressed', 'confused',
];

// ---------------------------------------------------------------------------
// Extra detail bank — adds realistic noise / completeness variation
// ---------------------------------------------------------------------------

const EXTRA_DETAILS = [
  'He\'s not moving at all.',
  'There\'s a lot of blood.',
  'She\'s conscious but very pale.',
  '',
  'I don\'t know what happened.',
  'Please hurry, he\'s getting worse.',
  'The children are outside.',
  '',
  'I called once already but no one came.',
  '',
];

// ---------------------------------------------------------------------------
// Generator options
// ---------------------------------------------------------------------------

export interface GeneratorOptions {
  count?: number;
  domain?: IncidentDomain;
  severity?: ScenarioTemplate['severity'];
  locationQuality?: 'complete' | 'partial' | 'vague' | 'mixed';
  seed?: number;
}

export interface GeneratedScenario {
  transcript: string;
  expected_domain: IncidentDomain;
  expected_subtype: string;
  severity: ScenarioTemplate['severity'];
  location_quality: 'complete' | 'partial' | 'vague';
}

// ---------------------------------------------------------------------------
// Simple seeded pseudo-random (no external deps)
// ---------------------------------------------------------------------------

function makePrng(seed: number) {
  let s = seed;
  return function next(max: number): number {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return Math.abs(s) % max;
  };
}

function pickFrom<T>(arr: T[], next: (n: number) => number): T {
  return arr[next(arr.length)] as T;
}

// ---------------------------------------------------------------------------
// Main generate function
// ---------------------------------------------------------------------------

export function generateScenarios(options: GeneratorOptions = {}): GeneratedScenario[] {
  const count = options.count ?? 10;
  const seed = options.seed ?? Date.now();
  const next = makePrng(seed);

  let pool = [...SCENARIO_TEMPLATES];

  if (options.domain) {
    pool = pool.filter((t) => t.domain === options.domain);
  }

  if (options.severity) {
    pool = pool.filter((t) => t.severity === options.severity);
  }

  if (pool.length === 0) {
    throw new Error('No templates match the provided filters');
  }

  const addressBanks: Record<string, string[]> = {
    complete: COMPLETE_ADDRESSES,
    partial: PARTIAL_ADDRESSES,
    vague: VAGUE_ADDRESSES,
    mixed: [...COMPLETE_ADDRESSES, ...PARTIAL_ADDRESSES, ...VAGUE_ADDRESSES],
  };

  const locationQuality = options.locationQuality ?? 'mixed';
  const addressBank = addressBanks[locationQuality] ?? addressBanks['mixed'];

  const results: GeneratedScenario[] = [];

  for (let i = 0; i < count; i++) {
    const template = pickFrom(pool, next);
    const address = pickFrom(addressBank, next);
    const callerAffect = pickFrom(CALLER_AFFECTS, next);
    const extraDetail = pickFrom(EXTRA_DETAILS, next);

    // Determine quality label from which bank the address came from
    let location_quality: GeneratedScenario['location_quality'];
    if (COMPLETE_ADDRESSES.includes(address)) location_quality = 'complete';
    else if (PARTIAL_ADDRESSES.includes(address)) location_quality = 'partial';
    else location_quality = 'vague';

    const transcript = template.generate({ address, callerAffect, extraDetail });

    results.push({
      transcript,
      expected_domain: template.domain,
      expected_subtype: template.subtype,
      severity: template.severity,
      location_quality,
    });
  }

  return results;
}
