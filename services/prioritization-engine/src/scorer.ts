import type { IncidentRecord, Triage, PriorityTier, IncidentDomain } from '@ng911/incident-schema';
import scoringRules from '../config/scoring-rules.json';

export const SCORING_VERSION = scoringRules.scoring_version;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ScoringResult extends Triage {
  scoring_version: string;
  score_breakdown: ScoreBreakdown[];
}

export interface ScoreBreakdown {
  reason_code: string;
  weight: number;
  description: string;
}

// ---------------------------------------------------------------------------
// Domain base score lookup
// ---------------------------------------------------------------------------

function getDomainBaseScore(domain: IncidentDomain): number {
  const bases = scoringRules.domain_base_scores as Record<string, number>;
  return bases[domain] ?? bases['unknown'] ?? 0.08;
}

// ---------------------------------------------------------------------------
// Priority tier determination
// ---------------------------------------------------------------------------

function determineTier(score: number): PriorityTier {
  const tiers = Object.entries(scoringRules.priority_tiers) as [
    PriorityTier,
    { min_score: number; label: string },
  ][];

  // Sort descending by min_score so highest threshold wins first
  tiers.sort(([, a], [, b]) => b.min_score - a.min_score);

  for (const [tier, config] of tiers) {
    if (score >= config.min_score) return tier;
  }

  return 'P4';
}

// ---------------------------------------------------------------------------
// Victim count contribution
// ---------------------------------------------------------------------------

function victimCountContribution(
  victimCount: number | null,
  hasMultipleVictimsIndicator: boolean,
): { weight: number; description: string } | null {
  const cfg = scoringRules.victim_count_multiplier;
  if (!cfg.enabled) return null;

  // Only fire this rule when victim count adds information beyond the
  // multiple_victims indicator (which already contributes its base weight)
  if (!hasMultipleVictimsIndicator && (victimCount === null || victimCount <= 1)) return null;

  let additionalVictims: number;

  if (victimCount === null) {
    // Unknown plural — use half of max as a conservative estimate
    additionalVictims = Math.round(cfg.max_contribution / cfg.per_additional_victim / 2);
  } else if (victimCount <= 1) {
    return null;
  } else {
    additionalVictims = victimCount - 1;
  }

  const raw = additionalVictims * cfg.per_additional_victim;
  const weight = Math.min(cfg.max_contribution, raw);

  return {
    weight,
    description:
      victimCount === null
        ? `${cfg.description} (unknown multiple — conservative estimate)`
        : `${cfg.description} (${victimCount} victims, +${additionalVictims} beyond baseline)`,
  };
}

// ---------------------------------------------------------------------------
// Main scoring function
// ---------------------------------------------------------------------------

/**
 * Score an incident record and return a triage result with reason codes.
 *
 * Every contributing factor is returned in score_breakdown, making the
 * priority assignment fully auditable and operator-reviewable.
 */
export function scoreIncident(record: IncidentRecord): ScoringResult {
  // Domain-specific base score (replaces flat 0.10 default)
  let score = getDomainBaseScore(record.incident.domain);
  const reasonCodes: string[] = [];
  const breakdown: ScoreBreakdown[] = [];

  // Record the base score contribution
  breakdown.push({
    reason_code: 'DOMAIN_BASE',
    weight: score,
    description: `Domain base score for ${record.incident.domain}`,
  });

  const indicators = new Set(record.incident.severity_indicators);

  // Apply indicator rules
  for (const rule of scoringRules.indicator_rules) {
    if (indicators.has(rule.indicator)) {
      score += rule.weight;
      reasonCodes.push(rule.reason_code);
      breakdown.push({
        reason_code: rule.reason_code,
        weight: rule.weight,
        description: rule.description,
      });
    }
  }

  // Victim count multiplier
  const victimContrib = victimCountContribution(
    record.incident.victim_count_estimate,
    indicators.has('multiple_victims'),
  );
  if (victimContrib !== null && victimContrib.weight > 0) {
    score += victimContrib.weight;
    reasonCodes.push(scoringRules.victim_count_multiplier.reason_code);
    breakdown.push({
      reason_code: scoringRules.victim_count_multiplier.reason_code,
      weight: victimContrib.weight,
      description: victimContrib.description,
    });
  }

  // Verification flags: surface uncertainty for operator review without
  // touching the score. Missing location or low parser confidence must never
  // lower the priority of an otherwise urgent incident.
  const flags = scoringRules.verification_flags;

  if (record.location.dispatchable_location_score < flags.low_location_confidence.threshold) {
    reasonCodes.push(flags.low_location_confidence.reason_code);
    breakdown.push({
      reason_code: flags.low_location_confidence.reason_code,
      weight: 0,
      description: flags.low_location_confidence.description,
    });
  }

  if (record.incident.confidence < flags.low_parse_confidence.threshold) {
    reasonCodes.push(flags.low_parse_confidence.reason_code);
    breakdown.push({
      reason_code: flags.low_parse_confidence.reason_code,
      weight: 0,
      description: flags.low_parse_confidence.description,
    });
  }

  const finalScore = Math.max(0, Math.min(1, score));
  const priorityTier = determineTier(finalScore);

  return {
    priority_score: Math.round(finalScore * 1000) / 1000,
    priority_tier: priorityTier,
    reason_codes: reasonCodes,
    scoring_version: SCORING_VERSION,
    score_breakdown: breakdown,
  };
}
