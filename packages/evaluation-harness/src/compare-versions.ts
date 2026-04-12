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
 * The "revised" config is evaluated by temporarily monkey-patching the
 * in-process module. Both runs share the same parser output so differences
 * are purely attributable to scoring config changes.
 */

import { readFileSync } from 'fs';
import { resolve } from 'path';
import { parseTranscript } from '@ng911/transcript-parser';
import type { IncidentRecord } from '@ng911/incident-schema';
import type { Fixture } from './types';

// ---------------------------------------------------------------------------
// Lightweight scorer that accepts an explicit config object, so we can
// test an alternative config without touching the installed package.
// ---------------------------------------------------------------------------

interface ScoringConfig {
  scoring_version: string;
  domain_base_scores: Record<string, number>;
  indicator_rules: Array<{ indicator: string; weight: number; reason_code: string; description: string }>;
  victim_count_multiplier: { enabled: boolean; per_additional_victim: number; max_contribution: number; reason_code: string; description: string };
  penalty_rules: {
    low_location_confidence: { threshold: number; penalty: number; reason_code: string; description: string };
    low_parse_confidence:    { threshold: number; penalty: number; reason_code: string; description: string };
  };
  priority_tiers: Record<string, { min_score: number; label: string }>;
}

function scoreWithConfig(record: IncidentRecord, cfg: ScoringConfig): { tier: string | null; score: number } {
  const base = (cfg.domain_base_scores[record.incident.domain] ?? cfg.domain_base_scores['unknown'] ?? 0.08);
  let score = base;
  const indicators = new Set(record.incident.severity_indicators);

  for (const rule of cfg.indicator_rules) {
    if (indicators.has(rule.indicator)) score += rule.weight;
  }

  const vc = cfg.victim_count_multiplier;
  if (vc.enabled && record.incident.victim_count_estimate !== null && record.incident.victim_count_estimate > 1) {
    score += Math.min(vc.max_contribution, (record.incident.victim_count_estimate - 1) * vc.per_additional_victim);
  }

  const p = cfg.penalty_rules;
  if (record.location.dispatchable_location_score < p.low_location_confidence.threshold) score += p.low_location_confidence.penalty;
  if (record.incident.confidence               < p.low_parse_confidence.threshold)    score += p.low_parse_confidence.penalty;

  const finalScore = Math.max(0, Math.min(1, score));

  const tiers = Object.entries(cfg.priority_tiers).sort(([, a], [, b]) => b.min_score - a.min_score);
  for (const [tier, { min_score }] of tiers) {
    if (finalScore >= min_score) return { tier, score: finalScore };
  }
  return { tier: 'P4', score: finalScore };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function parseArgs() {
  const args = process.argv.slice(2);
  let baselinePath = resolve(__dirname, '../../../services/prioritization-engine/config/scoring-rules.json');
  let revisedPath  = '';
  let fixturesPath = resolve(__dirname, '../../../data/fixtures/sample-incidents.json');

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--baseline' && args[i + 1]) baselinePath = resolve(args[++i]);
    if (args[i] === '--revised'  && args[i + 1]) revisedPath  = resolve(args[++i]);
    if (args[i] === '--fixtures' && args[i + 1]) fixturesPath = resolve(args[++i]);
  }
  return { baselinePath, revisedPath, fixturesPath };
}

const { baselinePath, revisedPath, fixturesPath } = parseArgs();

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
})).filter((f) => f.transcript.length > 0);

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const GREEN  = '\x1b[32m';
const RED    = '\x1b[31m';
const YELLOW = '\x1b[33m';
const DIM    = '\x1b[2m';

console.log(`\n${BOLD}Scoring Version Comparison${RESET}`);
console.log(`Baseline : v${baselineCfg.scoring_version}  (${baselinePath})`);
console.log(`Revised  : v${revisedCfg.scoring_version}  (${revisedPath})`);
console.log(`Fixtures : ${fixtures.length}\n`);
console.log('─'.repeat(80));

let improved = 0, degraded = 0, unchanged = 0;

for (const fixture of fixtures) {
  const parsed   = parseTranscript(fixture.transcript);
  const baseline = scoreWithConfig(parsed, baselineCfg);
  const revised  = scoreWithConfig(parsed, revisedCfg);

  const delta      = revised.score - baseline.score;
  const tierChange = baseline.tier !== revised.tier;
  const expected   = fixture.expected_priority_tier;

  // An "improvement" means revised tier matches expected better than baseline
  const baselineCorrect = baseline.tier === expected;
  const revisedCorrect  = revised.tier  === expected;
  const isImprovement   = !baselineCorrect && revisedCorrect;
  const isDegradation   = baselineCorrect  && !revisedCorrect;

  if (isImprovement) improved++;
  else if (isDegradation) degraded++;
  else unchanged++;

  const indicator = isImprovement ? `${GREEN}↑ improved${RESET}` : isDegradation ? `${RED}↓ degraded${RESET}` : `${DIM}  same${RESET}`;
  const tierStr   = tierChange
    ? `${baseline.tier} → ${revised.tier}`
    : `${baseline.tier} (unchanged)`;
  const deltaStr  = `${delta >= 0 ? '+' : ''}${delta.toFixed(3)}`;
  const deltaColor = delta > 0.01 ? GREEN : delta < -0.01 ? RED : DIM;

  console.log(`${BOLD}${fixture.id}${RESET}`);
  console.log(`  ${DIM}${fixture.transcript.slice(0, 70)}${fixture.transcript.length > 70 ? '…' : ''}${RESET}`);
  console.log(`  Tier: ${tierStr}   Score Δ: ${deltaColor}${deltaStr}${RESET}   Expected: ${expected}   ${indicator}`);
  console.log();
}

console.log('─'.repeat(80));
console.log(`\n${BOLD}Summary${RESET}`);
console.log(`  ${GREEN}Improved : ${improved}${RESET}`);
console.log(`  ${RED}Degraded : ${degraded}${RESET}`);
console.log(`  ${DIM}Unchanged: ${unchanged}${RESET}`);
console.log(`  Net change: ${improved - degraded >= 0 ? GREEN : RED}${improved - degraded >= 0 ? '+' : ''}${improved - degraded}${RESET}\n`);
