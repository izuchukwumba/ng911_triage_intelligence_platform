#!/usr/bin/env node
/**
 * Scoring Version Comparison CLI
 *
 * Replays a fixture set under two different scoring-rules.json files
 * and prints a diff table — showing which fixtures changed tier,
 * what the score delta was, and whether the change is an improvement.
 *
 * Usage:
 *   ts-node src/compare-versions.ts \
 *     --baseline ../../services/prioritization-engine/config/scoring-rules.json \
 *     --revised  ./config/scoring-rules-candidate.json \
 *     --fixtures ../../data/fixtures/sample-incidents.json
 *
 *   # Show only fixtures where the tier changed:
 *   ts-node src/compare-versions.ts --revised ./candidate.json --only-changed
 *
 *   # Show only regressions:
 *   ts-node src/compare-versions.ts --revised ./candidate.json --only-degraded
 *
 *   # Save full results as JSON for downstream processing:
 *   ts-node src/compare-versions.ts --revised ./candidate.json --json-output ./comparison.json
 *
 * The "revised" config is evaluated by passing it explicitly to the inline
 * scorer. Both runs share the same parser output so differences are purely
 * attributable to scoring config changes.
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';
import { parseTranscript } from '@ng911/transcript-parser';
import type { IncidentRecord } from '@ng911/incident-schema';
import type { Fixture } from './types';

// ---------------------------------------------------------------------------
// Lightweight scorer that accepts an explicit config object
// ---------------------------------------------------------------------------

interface ScoringConfig {
  scoring_version: string;
  domain_base_scores: Record<string, number>;
  indicator_rules: Array<{ indicator: string; weight: number; reason_code: string; description: string }>;
  victim_count_multiplier: { enabled: boolean; per_additional_victim: number; max_contribution: number; reason_code: string; description: string };
  // >= 0.3.0: uncertainty is flagged but never changes the score.
  verification_flags?: {
    low_location_confidence: { threshold: number; reason_code: string; description: string };
    low_parse_confidence:    { threshold: number; reason_code: string; description: string };
  };
  // <= 0.2.0: uncertainty was deducted from the score. Kept so older configs
  // can still be replayed exactly as they behaved.
  penalty_rules?: {
    low_location_confidence: { threshold: number; penalty: number; reason_code: string; description: string };
    low_parse_confidence:    { threshold: number; penalty: number; reason_code: string; description: string };
  };
  priority_tiers: Record<string, { min_score: number; label: string }>;
}

interface ScoreResult {
  tier: string | null;
  score: number;
  reason_codes: string[];
  breakdown: Array<{ reason_code: string; weight: number; description: string }>;
}

function scoreWithConfig(record: IncidentRecord, cfg: ScoringConfig): ScoreResult {
  const base = (cfg.domain_base_scores[record.incident.domain] ?? cfg.domain_base_scores['unknown'] ?? 0.08);
  let score = base;
  const indicators = new Set(record.incident.severity_indicators);
  const reason_codes: string[] = [];
  const breakdown: Array<{ reason_code: string; weight: number; description: string }> = [
    { reason_code: 'DOMAIN_BASE', weight: base, description: `Base score for ${record.incident.domain} domain` },
  ];

  for (const rule of cfg.indicator_rules) {
    if (indicators.has(rule.indicator)) {
      score += rule.weight;
      reason_codes.push(rule.reason_code);
      breakdown.push({ reason_code: rule.reason_code, weight: rule.weight, description: rule.description });
    }
  }

  const vc = cfg.victim_count_multiplier;
  if (vc.enabled && record.incident.victim_count_estimate !== null && record.incident.victim_count_estimate > 1) {
    const w = Math.min(vc.max_contribution, (record.incident.victim_count_estimate - 1) * vc.per_additional_victim);
    score += w;
    reason_codes.push(vc.reason_code);
    breakdown.push({ reason_code: vc.reason_code, weight: w, description: vc.description });
  }

  const rules = cfg.verification_flags ?? cfg.penalty_rules;
  if (rules) {
    const checks = [
      { rule: rules.low_location_confidence, fires: record.location.dispatchable_location_score < rules.low_location_confidence.threshold },
      { rule: rules.low_parse_confidence,    fires: record.incident.confidence < rules.low_parse_confidence.threshold },
    ];
    for (const { rule, fires } of checks) {
      if (!fires) continue;
      const weight = (rule as { penalty?: number }).penalty ?? 0;
      score += weight;
      reason_codes.push(rule.reason_code);
      breakdown.push({ reason_code: rule.reason_code, weight, description: rule.description });
    }
  }

  const finalScore = Math.max(0, Math.min(1, score));

  const tiers = Object.entries(cfg.priority_tiers).sort(([, a], [, b]) => b.min_score - a.min_score);
  for (const [tier, { min_score }] of tiers) {
    if (finalScore >= min_score) return { tier, score: finalScore, reason_codes, breakdown };
  }
  return { tier: 'P4', score: finalScore, reason_codes, breakdown };
}

// ---------------------------------------------------------------------------
// Args
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  let baselinePath = resolve(__dirname, '../../../services/prioritization-engine/config/scoring-rules.json');
  let revisedPath  = '';
  let fixturesPath = resolve(__dirname, '../../../data/fixtures/sample-incidents.json');
  let onlyChanged  = false;
  let onlyDegraded = false;
  let jsonOutput: string | null = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--baseline'    && args[i + 1]) baselinePath = resolve(args[++i]);
    if (args[i] === '--revised'     && args[i + 1]) revisedPath  = resolve(args[++i]);
    if (args[i] === '--fixtures'    && args[i + 1]) fixturesPath = resolve(args[++i]);
    if (args[i] === '--json-output' && args[i + 1]) jsonOutput   = resolve(args[++i]);
    if (args[i] === '--only-changed')  onlyChanged  = true;
    if (args[i] === '--only-degraded') onlyDegraded = true;
  }
  return { baselinePath, revisedPath, fixturesPath, onlyChanged, onlyDegraded, jsonOutput };
}

const { baselinePath, revisedPath, fixturesPath, onlyChanged, onlyDegraded, jsonOutput } = parseArgs();

if (!revisedPath) {
  console.error('--revised <path> is required');
  process.exit(1);
}

const baselineCfg = JSON.parse(readFileSync(baselinePath, 'utf-8')) as ScoringConfig;
const revisedCfg  = JSON.parse(readFileSync(revisedPath,  'utf-8')) as ScoringConfig;
const rawFixtures = JSON.parse(readFileSync(fixturesPath, 'utf-8')) as Array<Record<string, unknown>>;

const fixtures: Fixture[] = rawFixtures.map((r, i) => ({
  id:                     String(r['id'] ?? `fixture-${i + 1}`),
  transcript:             String(r['transcript'] ?? r['text'] ?? ''),
  expected_domain:        String(r['expected_domain'] ?? 'unknown'),
  expected_subtype:       String(r['expected_subtype'] ?? 'unclassified'),
  expected_priority_tier: String(r['expected_priority_tier'] ?? 'P4'),
  severity:               String(r['severity'] ?? 'unknown'),
  notes:                  r['notes'] ? String(r['notes']) : undefined,
})).filter((f) => f.transcript.length > 0);

// ---------------------------------------------------------------------------
// ANSI helpers
// ---------------------------------------------------------------------------

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const GREEN  = '\x1b[32m';
const RED    = '\x1b[31m';
const YELLOW = '\x1b[33m';
const DIM    = '\x1b[2m';
const CYAN   = '\x1b[36m';

function tierColor(tier: string | null): string {
  const map: Record<string, string> = { P0: RED, P1: YELLOW, P2: YELLOW, P3: GREEN, P4: DIM };
  return map[tier ?? ''] ?? RESET;
}

// ---------------------------------------------------------------------------
// Run comparison
// ---------------------------------------------------------------------------

console.log(`\n${BOLD}Scoring Version Comparison${RESET}`);
console.log(`Baseline : v${baselineCfg.scoring_version}  ${DIM}${baselinePath}${RESET}`);
console.log(`Revised  : v${revisedCfg.scoring_version}  ${DIM}${revisedPath}${RESET}`);
console.log(`Fixtures : ${fixtures.length}`);
if (onlyChanged)  console.log(`Filter   : ${YELLOW}--only-changed${RESET} (showing tier-change fixtures only)`);
if (onlyDegraded) console.log(`Filter   : ${RED}--only-degraded${RESET} (showing regressions only)`);
console.log('─'.repeat(80));

interface ComparisonResult {
  fixture_id: string;
  transcript_excerpt: string;
  expected_tier: string;
  baseline_tier: string | null;
  revised_tier: string | null;
  baseline_score: number;
  revised_score: number;
  score_delta: number;
  tier_changed: boolean;
  baseline_correct: boolean;
  revised_correct: boolean;
  is_improvement: boolean;
  is_degradation: boolean;
  reason_codes_added: string[];
  reason_codes_removed: string[];
}

let improved = 0, degraded = 0, unchanged = 0;
const allResults: ComparisonResult[] = [];

// Tier transition matrix: baseline_tier -> revised_tier -> count
const transitionMatrix: Record<string, Record<string, number>> = {};

for (const fixture of fixtures) {
  const parsed   = parseTranscript(fixture.transcript);
  const baseline = scoreWithConfig(parsed, baselineCfg);
  const revised  = scoreWithConfig(parsed, revisedCfg);

  const delta      = revised.score - baseline.score;
  const tierChange = baseline.tier !== revised.tier;
  const expected   = fixture.expected_priority_tier;

  const baselineCorrect = baseline.tier === expected;
  const revisedCorrect  = revised.tier  === expected;
  const isImprovement   = !baselineCorrect && revisedCorrect;
  const isDegradation   = baselineCorrect  && !revisedCorrect;

  if (isImprovement) improved++;
  else if (isDegradation) degraded++;
  else unchanged++;

  // Build transition matrix entry
  const bTier = baseline.tier ?? 'null';
  const rTier = revised.tier ?? 'null';
  if (!transitionMatrix[bTier]) transitionMatrix[bTier] = {};
  transitionMatrix[bTier][rTier] = (transitionMatrix[bTier][rTier] ?? 0) + 1;

  const result: ComparisonResult = {
    fixture_id:           fixture.id,
    transcript_excerpt:   fixture.transcript.slice(0, 70),
    expected_tier:        expected,
    baseline_tier:        baseline.tier,
    revised_tier:         revised.tier,
    baseline_score:       Math.round(baseline.score * 1000) / 1000,
    revised_score:        Math.round(revised.score * 1000) / 1000,
    score_delta:          Math.round(delta * 1000) / 1000,
    tier_changed:         tierChange,
    baseline_correct:     baselineCorrect,
    revised_correct:      revisedCorrect,
    is_improvement:       isImprovement,
    is_degradation:       isDegradation,
    reason_codes_added:   revised.reason_codes.filter((c) => !baseline.reason_codes.includes(c)),
    reason_codes_removed: baseline.reason_codes.filter((c) => !revised.reason_codes.includes(c)),
  };
  allResults.push(result);
}

// Apply display filters
const displayResults = allResults.filter((r) => {
  if (onlyDegraded) return r.is_degradation;
  if (onlyChanged)  return r.tier_changed;
  return true;
});

for (const r of displayResults) {
  const indicator = r.is_improvement
    ? `${GREEN}↑ improved${RESET}`
    : r.is_degradation
      ? `${RED}↓ degraded${RESET}`
      : `${DIM}  same${RESET}`;

  const tierStr = r.tier_changed
    ? `${tierColor(r.baseline_tier)}${r.baseline_tier}${RESET} → ${tierColor(r.revised_tier)}${r.revised_tier}${RESET}`
    : `${tierColor(r.baseline_tier)}${r.baseline_tier}${RESET} ${DIM}(unchanged)${RESET}`;

  const deltaStr   = `${r.score_delta >= 0 ? '+' : ''}${r.score_delta.toFixed(3)}`;
  const deltaColor = r.score_delta > 0.01 ? GREEN : r.score_delta < -0.01 ? RED : DIM;

  console.log(`${BOLD}${r.fixture_id}${RESET}  Expected: ${r.expected_tier}   ${indicator}`);
  console.log(`  ${DIM}${r.transcript_excerpt}${r.transcript_excerpt.length >= 70 ? '…' : ''}${RESET}`);
  console.log(`  Tier: ${tierStr}   Score: ${r.baseline_score.toFixed(3)} → ${r.revised_score.toFixed(3)}  Δ ${deltaColor}${deltaStr}${RESET}`);
  if (r.reason_codes_added.length > 0)   console.log(`  ${GREEN}+ Codes added   : ${r.reason_codes_added.join(', ')}${RESET}`);
  if (r.reason_codes_removed.length > 0) console.log(`  ${RED}− Codes removed : ${r.reason_codes_removed.join(', ')}${RESET}`);
  console.log();
}

// ---------------------------------------------------------------------------
// Tier transition matrix
// ---------------------------------------------------------------------------

const tiers = ['P0', 'P1', 'P2', 'P3', 'P4'];

console.log('─'.repeat(80));
console.log(`\n${BOLD}Tier Transition Matrix${RESET}  ${DIM}(row = baseline tier, col = revised tier)${RESET}\n`);

const colWidth = 8;
const header = '          ' + tiers.map((t) => t.padStart(colWidth)).join('');
console.log(header);
console.log('  ' + '─'.repeat(header.length - 2));

for (const bTier of tiers) {
  const row = transitionMatrix[bTier] ?? {};
  const rowTotal = Object.values(row).reduce((a, b) => a + b, 0);
  if (rowTotal === 0) continue;

  let line = `  ${BOLD}${bTier}${RESET}       `;
  for (const rTier of tiers) {
    const count = row[rTier] ?? 0;
    const cell  = count === 0 ? '·' : String(count);
    const color = bTier === rTier ? DIM : count > 0 && bTier !== rTier ? (tierRank(rTier) < tierRank(bTier) ? CYAN : YELLOW) : '';
    line += `${color}${cell.padStart(colWidth)}${RESET}`;
  }
  console.log(line);
}
console.log();

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

console.log('─'.repeat(80));
console.log(`\n${BOLD}Summary${RESET}`);
console.log(`  ${GREEN}Improved : ${improved}${RESET}   (baseline wrong → revised correct)`);
console.log(`  ${RED}Degraded : ${degraded}${RESET}   (baseline correct → revised wrong)`);
console.log(`  ${DIM}Unchanged: ${unchanged}${RESET}`);

const net = improved - degraded;
const netColor = net > 0 ? GREEN : net < 0 ? RED : DIM;
console.log(`  Net change: ${netColor}${net >= 0 ? '+' : ''}${net}${RESET}\n`);

if (degraded > 0) {
  console.log(`  ${RED}${BOLD}Regressions detected — review before bumping scoring_version${RESET}`);
} else if (improved > 0) {
  console.log(`  ${GREEN}No regressions. Safe to bump scoring_version if manual review passes.${RESET}`);
} else {
  console.log(`  ${DIM}No tier-level changes. Score deltas may still be meaningful — use --json-output for details.${RESET}`);
}

console.log();

// ---------------------------------------------------------------------------
// JSON output
// ---------------------------------------------------------------------------

if (jsonOutput) {
  const output = {
    run_at:           new Date().toISOString(),
    baseline_version: baselineCfg.scoring_version,
    revised_version:  revisedCfg.scoring_version,
    fixtures_count:   fixtures.length,
    summary: { improved, degraded, unchanged, net: improved - degraded },
    transition_matrix: transitionMatrix,
    results: allResults,
  };
  writeFileSync(jsonOutput, JSON.stringify(output, null, 2), 'utf-8');
  console.log(`Full comparison saved to ${CYAN}${jsonOutput}${RESET}\n`);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function tierRank(tier: string | null): number {
  const map: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
  return map[tier ?? ''] ?? 99;
}
