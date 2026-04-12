import type { EvaluationReport, FixtureResult, ScoreBreakdownEntry, BucketResult, LatencyStats } from './types';

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function bar(n: number, width = 20): string {
  const filled = Math.round(n * width);
  return '█'.repeat(filled) + '░'.repeat(width - filled);
}

function tierColor(tier: string | null): string {
  const map: Record<string, string> = { P0: '\x1b[31m', P1: '\x1b[33m', P2: '\x1b[33m', P3: '\x1b[32m', P4: '\x1b[90m' };
  return map[tier ?? ''] ?? '\x1b[0m';
}

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const GREEN  = '\x1b[32m';
const RED    = '\x1b[31m';
const YELLOW = '\x1b[33m';
const DIM    = '\x1b[2m';
const CYAN   = '\x1b[36m';

const TIER_LABELS: Record<string, string> = {
  P0: 'IMMEDIATE (life-threatening)',
  P1: 'URGENT (high severity)',
  P2: 'ELEVATED (moderate severity)',
  P3: 'STANDARD (low-moderate)',
  P4: 'NON-URGENT / edge-case',
};

// ---------------------------------------------------------------------------
// Main report entry point
// ---------------------------------------------------------------------------

export function printReport(report: EvaluationReport): void {
  const hr  = '─'.repeat(72);
  const hr2 = '━'.repeat(72);

  console.log(`\n${BOLD}NG911 Triage Intelligence Platform — Evaluation Report${RESET}`);
  console.log(hr2);
  console.log(`Run at:          ${report.run_at}`);
  console.log(`Parser version:  ${report.parser_version}   Scoring version: ${report.scoring_version}`);
  console.log(`Fixtures run:    ${report.total_fixtures}`);
  console.log(hr2);

  // ── 1. Accuracy Metrics ──────────────────────────────────────────────────
  console.log(`\n${BOLD}§1  Accuracy Metrics${RESET}`);
  console.log(hr);

  const accuracyRows: Array<{ label: string; val: number; target: number; note: string }> = [
    { label: 'Domain accuracy',   val: report.domain_accuracy,   target: 0.90, note: 'target ≥ 90%' },
    { label: 'Subtype accuracy',  val: report.subtype_accuracy,  target: 0.75, note: 'target ≥ 75%' },
    { label: 'Tier accuracy',     val: report.tier_accuracy,     target: 0.80, note: 'target ≥ 80%' },
  ];

  for (const { label, val, target, note } of accuracyRows) {
    const pass  = val >= target;
    const color = pass ? GREEN : val >= target * 0.85 ? YELLOW : RED;
    const status = pass ? `${GREEN}✓${RESET}` : `${RED}✗${RESET}`;
    console.log(`  ${status} ${label.padEnd(20)} ${color}${bar(val)}${RESET}  ${color}${pct(val)}${RESET}  ${DIM}${note}${RESET}`);
  }

  // ── 2. P0 Safety Metrics ─────────────────────────────────────────────────
  console.log(`\n${BOLD}§2  P0 Safety Metrics${RESET}  ${DIM}(most operationally significant)${RESET}`);
  console.log(hr);

  const fpPass = report.false_p0_rate  <= 0.05;
  const mpPass = report.missed_p0_rate <= 0.10;
  const fpColor = fpPass ? GREEN : report.false_p0_rate  <= 0.10 ? YELLOW : RED;
  const mpColor = mpPass ? GREEN : report.missed_p0_rate <= 0.20 ? YELLOW : RED;

  console.log(`  ${fpPass ? `${GREEN}✓${RESET}` : `${RED}✗${RESET}`} False-P0 rate    ${fpColor}${pct(report.false_p0_rate)}${RESET}   (system said P0, expected was not P0)  ${DIM}target ≤ 5%${RESET}`);
  console.log(`  ${mpPass ? `${GREEN}✓${RESET}` : `${RED}✗${RESET}`} Missed-P0 rate   ${mpColor}${pct(report.missed_p0_rate)}${RESET}   (expected P0, system missed it)        ${DIM}target ≤ 10%${RESET}`);

  const p0Fixtures = report.results.filter((r) => r.expected_tier === 'P0');
  if (p0Fixtures.length > 0) {
    const p0Correct = p0Fixtures.filter((r) => r.tier_correct).length;
    console.log(`\n  ${DIM}P0 fixtures in this run: ${p0Fixtures.length}  |  correctly identified: ${p0Correct}  |  recall: ${pct(p0Correct / p0Fixtures.length)}${RESET}`);
  }

  // ── 3. Scenario Buckets ───────────────────────────────────────────────────
  console.log(`\n${BOLD}§3  Scenario Buckets${RESET}  ${DIM}(tier accuracy per expected priority level)${RESET}`);
  console.log(hr);

  for (const bucket of report.bucket_results) {
    const color = bucket.accuracy === 1 ? GREEN : bucket.accuracy >= 0.75 ? YELLOW : RED;
    const tierLabel = TIER_LABELS[bucket.tier] ?? bucket.tier;
    console.log(
      `  ${tierColor(bucket.tier)}${bucket.tier}${RESET}  ${color}${bar(bucket.accuracy, 12)}${RESET}  ` +
      `${color}${pct(bucket.accuracy)}${RESET}  ${bucket.correct}/${bucket.total}  ${DIM}${tierLabel}${RESET}`,
    );
  }

  // ── 4. Score Distribution ─────────────────────────────────────────────────
  console.log(`\n${BOLD}§4  Score Distribution${RESET}  ${DIM}(actual tiers assigned by the system)${RESET}`);
  console.log(hr);

  const dist = report.score_distribution;
  for (const tier of ['P0', 'P1', 'P2', 'P3', 'P4']) {
    const count = dist[tier] ?? 0;
    const frac  = count / report.total_fixtures;
    console.log(`  ${tierColor(tier)}${tier}${RESET}  ${bar(frac, 15)}  ${String(count).padStart(2)} fixture${count !== 1 ? 's' : ' '}  ${pct(frac)}`);
  }

  // ── 5. Latency Profile ────────────────────────────────────────────────────
  console.log(`\n${BOLD}§5  Latency Profile${RESET}  ${DIM}(parse + score, wall-clock time per fixture)${RESET}`);
  console.log(hr);

  const { mean_ms, p50_ms, p95_ms, min_ms, max_ms } = report.latency;
  const latColor = mean_ms <= 20 ? GREEN : mean_ms <= 50 ? YELLOW : RED;

  console.log(`  Mean       ${latColor}${mean_ms}ms${RESET}`);
  console.log(`  P50        ${p50_ms}ms`);
  console.log(`  P95        ${p95_ms}ms`);
  console.log(`  Min / Max  ${min_ms}ms / ${max_ms}ms`);
  console.log(`  ${DIM}(deterministic rules pipeline — no model inference, no I/O on the hot path)${RESET}`);

  // ── 6. Per-Fixture Results ────────────────────────────────────────────────
  console.log(`\n${BOLD}§6  Per-Fixture Results${RESET}`);
  console.log(hr);

  for (const r of report.results) {
    printFixtureRow(r);
  }
  console.log(hr);

  // ── 7. Failure Analysis ───────────────────────────────────────────────────
  const failures = report.results.filter((r) => !r.tier_correct);
  if (failures.length > 0) {
    printFailureAnalysis(failures, report.total_fixtures);
  }

  // ── Summary line ──────────────────────────────────────────────────────────
  const passed = report.results.filter((r) => r.tier_correct).length;
  const summaryColor = passed === report.total_fixtures ? GREEN : passed >= report.total_fixtures * 0.8 ? YELLOW : RED;
  console.log(`\n${summaryColor}${BOLD}${passed}/${report.total_fixtures} fixtures matched expected tier${RESET}  ` +
    `${DIM}domain: ${pct(report.domain_accuracy)}  subtype: ${pct(report.subtype_accuracy)}  ` +
    `false-P0: ${pct(report.false_p0_rate)}  missed-P0: ${pct(report.missed_p0_rate)}${RESET}\n`);
}

// ---------------------------------------------------------------------------
// Per-fixture row
// ---------------------------------------------------------------------------

function printFixtureRow(r: FixtureResult): void {
  const mark     = r.tier_correct   ? `${GREEN}✓${RESET}` : `${RED}✗${RESET}`;
  const domainMk = r.domain_correct ? '' : ` ${RED}(domain: got ${r.actual_domain})${RESET}`;
  const tierMk   = r.tier_correct   ? '' : ` ${RED}(expected ${r.expected_tier}, got ${r.actual_tier})${RESET}`;

  console.log(`\n  ${mark} ${BOLD}${r.fixture_id}${RESET}${domainMk}${tierMk}  ${DIM}${r.parse_score_ms}ms${RESET}`);
  console.log(`     ${DIM}${r.transcript_excerpt}${RESET}`);
  console.log(
    `     Score: ${r.priority_score?.toFixed(3) ?? '—'}  ` +
    `Tier: ${tierColor(r.actual_tier)}${r.actual_tier ?? '—'}${RESET}  ` +
    `Lang: ${r.language_detected ?? '—'}  Stress: ${r.caller_stress ?? '—'}  ` +
    `Loc: ${(r.location_quality * 100).toFixed(0)}%`,
  );
  if (r.reason_codes.length > 0) {
    console.log(`     Codes: ${DIM}${r.reason_codes.join(', ')}${RESET}`);
  }

  // Inline score breakdown for failed fixtures only
  if (!r.tier_correct && r.score_breakdown.length > 0) {
    console.log(`     ${YELLOW}Score breakdown (why this score?):${RESET}`);
    for (const entry of r.score_breakdown) {
      const sign   = entry.weight >= 0 ? '+' : '';
      const wColor = entry.weight >= 0 ? CYAN : RED;
      console.log(`       ${wColor}${sign}${entry.weight.toFixed(3)}${RESET}  ${entry.reason_code.padEnd(30)}  ${DIM}${entry.description}${RESET}`);
    }
  }
}

// ---------------------------------------------------------------------------
// Failure analysis
// ---------------------------------------------------------------------------

function printFailureAnalysis(failures: FixtureResult[], total: number): void {
  const hr = '─'.repeat(72);
  console.log(`\n${BOLD}§7  Failure Analysis${RESET}  ${RED}${failures.length} fixture(s) with incorrect tier${RESET}`);
  console.log(hr);

  const overTriage  = failures.filter((r) => tierRank(r.actual_tier) < tierRank(r.expected_tier));
  const underTriage = failures.filter((r) => tierRank(r.actual_tier) > tierRank(r.expected_tier));
  const domainWrong = failures.filter((r) => !r.domain_correct);

  if (overTriage.length > 0) {
    console.log(`\n  ${RED}Over-triaged — scored too high (${overTriage.length}):${RESET}`);
    for (const r of overTriage) {
      console.log(`    • ${BOLD}${r.fixture_id}${RESET}  expected ${r.expected_tier} → got ${tierColor(r.actual_tier)}${r.actual_tier}${RESET}  score ${r.priority_score?.toFixed(3) ?? '—'}`);
      const top = [...r.score_breakdown].filter((b) => b.weight > 0 && b.reason_code !== 'DOMAIN_BASE').sort((a, b) => b.weight - a.weight)[0];
      if (top) console.log(`      ${DIM}Largest positive contributor: ${top.reason_code} (+${top.weight.toFixed(3)})${RESET}`);
      if (r.notes) console.log(`      ${YELLOW}Note: ${r.notes}${RESET}`);
    }
  }

  if (underTriage.length > 0) {
    console.log(`\n  ${RED}Under-triaged — scored too low (${underTriage.length}):${RESET}`);
    for (const r of underTriage) {
      console.log(`    • ${BOLD}${r.fixture_id}${RESET}  expected ${r.expected_tier} → got ${tierColor(r.actual_tier)}${r.actual_tier}${RESET}  score ${r.priority_score?.toFixed(3) ?? '—'}`);
      const penalties = r.score_breakdown.filter((e) => e.weight < 0);
      if (penalties.length > 0) {
        console.log(`      ${DIM}Penalties: ${penalties.map((p) => `${p.reason_code} (${p.weight.toFixed(3)})`).join(', ')}${RESET}`);
      }
      if (r.notes) console.log(`      ${YELLOW}Note: ${r.notes}${RESET}`);
    }
  }

  if (domainWrong.length > 0) {
    console.log(`\n  ${YELLOW}Domain misclassification (${domainWrong.length}):${RESET}`);
    for (const r of domainWrong) {
      console.log(`    • ${BOLD}${r.fixture_id}${RESET}  expected domain ${r.expected_domain} → got ${r.actual_domain}`);
    }
  }

  console.log(`\n  ${DIM}${failures.length}/${total} failures  |  over-triaged: ${overTriage.length}  under-triaged: ${underTriage.length}  domain wrong: ${domainWrong.length}${RESET}`);
  console.log(hr);
}

// P0=0, P1=1, ..., P4=4  (lower rank = higher priority)
function tierRank(tier: string | null): number {
  const map: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
  return map[tier ?? ''] ?? 99;
}
