export interface Fixture {
  id: string;
  transcript: string;
  expected_domain: string;
  expected_subtype: string;
  expected_priority_tier: string;
  severity: string;
  notes?: string;
}

export interface ScoreBreakdownEntry {
  reason_code: string;
  weight: number;
  description: string;
}

export interface FixtureResult {
  fixture_id: string;
  transcript_excerpt: string;
  expected_domain: string;
  actual_domain: string;
  domain_correct: boolean;
  expected_subtype: string;
  actual_subtype: string;
  subtype_correct: boolean;
  expected_tier: string;
  actual_tier: string | null;
  tier_correct: boolean;
  priority_score: number | null;
  score_breakdown: ScoreBreakdownEntry[];
  reason_codes: string[];
  language_detected: string | null;
  caller_stress: string | null;
  location_quality: number;
  parse_score_ms: number;
  notes?: string;
}

export interface BucketResult {
  tier: string;
  total: number;
  correct: number;
  accuracy: number;
}

export interface LatencyStats {
  mean_ms: number;
  p50_ms: number;
  p95_ms: number;
  min_ms: number;
  max_ms: number;
}

export interface EvaluationReport {
  run_at: string;
  parser_version: string;
  scoring_version: string;
  total_fixtures: number;
  domain_accuracy: number;
  subtype_accuracy: number;
  tier_accuracy: number;
  false_p0_rate: number;
  missed_p0_rate: number;
  score_distribution: Record<string, number>;
  bucket_results: BucketResult[];
  latency: LatencyStats;
  results: FixtureResult[];
}
