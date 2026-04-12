import { parseTranscript, PARSER_VERSION } from '@ng911/transcript-parser';
import { scoreIncident, SCORING_VERSION } from '@ng911/prioritization-engine';
import type { Fixture, FixtureResult, EvaluationReport } from './types';

export function runFixture(fixture: Fixture): FixtureResult {
  const parsed   = parseTranscript(fixture.transcript);
  const scoring  = scoreIncident(parsed);

  const merged = {
    ...parsed,
    triage: {
      priority_score: scoring.priority_score,
      priority_tier:  scoring.priority_tier,
      reason_codes:   scoring.reason_codes,
    },
    audit: { ...parsed.audit, scoring_version: scoring.scoring_version },
  };

  return {
    fixture_id:       fixture.id,
    transcript_excerpt: fixture.transcript.slice(0, 80) + (fixture.transcript.length > 80 ? '…' : ''),
    expected_domain:  fixture.expected_domain,
    actual_domain:    merged.incident.domain,
    domain_correct:   merged.incident.domain === fixture.expected_domain,
    expected_subtype: fixture.expected_subtype,
    actual_subtype:   merged.incident.subtype,
    subtype_correct:  merged.incident.subtype === fixture.expected_subtype,
    expected_tier:    fixture.expected_priority_tier,
    actual_tier:      merged.triage.priority_tier,
    tier_correct:     merged.triage.priority_tier === fixture.expected_priority_tier,
    priority_score:   merged.triage.priority_score,
    score_breakdown:  scoring.score_breakdown,
    reason_codes:     merged.triage.reason_codes,
    language_detected: merged.caller_context.language_hint,
    caller_stress:    merged.caller_context.caller_stress_level,
    location_quality: merged.location.dispatchable_location_score,
    notes:            fixture.notes,
  };
}

export function buildReport(fixtures: Fixture[]): EvaluationReport {
  const results = fixtures.map(runFixture);

  const total = results.length;
  if (total === 0) throw new Error('No fixtures provided');

  const domainCorrect   = results.filter((r) => r.domain_correct).length;
  const subtypeCorrect  = results.filter((r) => r.subtype_correct).length;
  const tierCorrect     = results.filter((r) => r.tier_correct).length;

  // False-P0: system said P0 but expected was not P0
  const falseP0 = results.filter((r) => r.actual_tier === 'P0' && r.expected_tier !== 'P0').length;
  // Missed-P0: expected P0 but system did not assign P0
  const missedP0 = results.filter((r) => r.expected_tier === 'P0' && r.actual_tier !== 'P0').length;
  const expectedP0Count = results.filter((r) => r.expected_tier === 'P0').length;
  const nonP0Count = total - expectedP0Count;

  const scoreDistribution: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0, P4: 0, null: 0 };
  for (const r of results) {
    const tier = r.actual_tier ?? 'null';
    scoreDistribution[tier] = (scoreDistribution[tier] ?? 0) + 1;
  }

  return {
    run_at:          new Date().toISOString(),
    parser_version:  PARSER_VERSION,
    scoring_version: SCORING_VERSION,
    total_fixtures:  total,
    domain_accuracy:  round(domainCorrect / total),
    subtype_accuracy: round(subtypeCorrect / total),
    tier_accuracy:    round(tierCorrect / total),
    false_p0_rate:    nonP0Count > 0 ? round(falseP0 / nonP0Count) : 0,
    missed_p0_rate:   expectedP0Count > 0 ? round(missedP0 / expectedP0Count) : 0,
    score_distribution: scoreDistribution,
    results,
  };
}

function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}
