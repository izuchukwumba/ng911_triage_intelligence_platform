import { parseTranscript, PARSER_VERSION } from '@ng911/transcript-parser';
import { scoreIncident, SCORING_VERSION } from '@ng911/prioritization-engine';
import type { Fixture, FixtureResult, EvaluationReport, BucketResult, LatencyStats } from './types';

export function runFixture(fixture: Fixture): FixtureResult {
  const t0      = Date.now();
  const parsed  = parseTranscript(fixture.transcript);
  const scoring = scoreIncident(parsed);
  const parse_score_ms = Date.now() - t0;

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
    fixture_id:          fixture.id,
    transcript_excerpt:  fixture.transcript.slice(0, 80) + (fixture.transcript.length > 80 ? '…' : ''),
    expected_domain:     fixture.expected_domain,
    actual_domain:       merged.incident.domain,
    domain_correct:      merged.incident.domain === fixture.expected_domain,
    expected_subtype:    fixture.expected_subtype,
    actual_subtype:      merged.incident.subtype,
    subtype_correct:     merged.incident.subtype === fixture.expected_subtype,
    expected_tier:       fixture.expected_priority_tier,
    actual_tier:         merged.triage.priority_tier,
    tier_correct:        merged.triage.priority_tier === fixture.expected_priority_tier,
    priority_score:      merged.triage.priority_score,
    score_breakdown:     scoring.score_breakdown,
    reason_codes:        merged.triage.reason_codes,
    language_detected:   merged.caller_context.language_hint,
    caller_stress:       merged.caller_context.caller_stress_level,
    location_quality:    merged.location.dispatchable_location_score,
    parse_score_ms,
    notes:               fixture.notes,
  };
}

export function buildReport(fixtures: Fixture[]): EvaluationReport {
  const results = fixtures.map(runFixture);

  const total = results.length;
  if (total === 0) throw new Error('No fixtures provided');

  const domainCorrect   = results.filter((r) => r.domain_correct).length;
  const subtypeCorrect  = results.filter((r) => r.subtype_correct).length;
  const tierCorrect     = results.filter((r) => r.tier_correct).length;

  const falseP0        = results.filter((r) => r.actual_tier === 'P0' && r.expected_tier !== 'P0').length;
  const missedP0       = results.filter((r) => r.expected_tier === 'P0' && r.actual_tier !== 'P0').length;
  const expectedP0Count = results.filter((r) => r.expected_tier === 'P0').length;
  const nonP0Count      = total - expectedP0Count;

  const scoreDistribution: Record<string, number> = { P0: 0, P1: 0, P2: 0, P3: 0, P4: 0, null: 0 };
  for (const r of results) {
    const tier = r.actual_tier ?? 'null';
    scoreDistribution[tier] = (scoreDistribution[tier] ?? 0) + 1;
  }

  // Scenario bucket results — grouped by expected tier
  const bucketMap: Record<string, FixtureResult[]> = {};
  for (const r of results) {
    if (!bucketMap[r.expected_tier]) bucketMap[r.expected_tier] = [];
    bucketMap[r.expected_tier].push(r);
  }
  const bucket_results: BucketResult[] = ['P0', 'P1', 'P2', 'P3', 'P4']
    .filter((tier) => (bucketMap[tier]?.length ?? 0) > 0)
    .map((tier) => {
      const group   = bucketMap[tier]!;
      const correct = group.filter((r) => r.tier_correct).length;
      return { tier, total: group.length, correct, accuracy: round(correct / group.length) };
    });

  // Latency statistics
  const latencies = [...results.map((r) => r.parse_score_ms)].sort((a, b) => a - b);
  const latency: LatencyStats = {
    mean_ms: Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length),
    p50_ms:  latencies[Math.floor(latencies.length * 0.50)] ?? 0,
    p95_ms:  latencies[Math.max(0, Math.ceil(latencies.length * 0.95) - 1)] ?? 0,
    min_ms:  latencies[0] ?? 0,
    max_ms:  latencies[latencies.length - 1] ?? 0,
  };

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
    bucket_results,
    latency,
    results,
  };
}

function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}
