import type { EvaluationReport, FixtureResult, ScoreBreakdownEntry } from './types';

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

export function printReport(report: EvaluationReport): void {
  const hr = '─'.repeat(72);
  console.log(`\n${BOLD}NG911 Evaluation Report${RESET}  ${DIM}${report.run_at}${RESET}`);
  console.log(hr);
  console.log(`Parser version:  ${report.parser_version}   Scoring version: ${report.scoring_version}`);
  console.log(`Fixtures run:    ${report.total_fixtures}`);
  console.log(hr);

  console.log(`\n${BOLD}Accuracy Metrics${RESET}`);
  const metrics = [
    ['Domain accuracy',   report.domain_accuracy],
    ['Subtype accuracy',  report.subtype_accuracy],
    ['Tier accuracy',     report.tier_accuracy],
  ] as [string, number][];

  for (const [label, val] of metrics) {
    const color = val >= 0.9 ? GREEN : val >= 0.7 ? YELLOW : RED;
    console.log(`  ${label.padEnd(20)} ${color}${bar(val)}${RESET}  ${color}${pct(val)}${RESET}`);
  }

  console.log(`\n${BOLD}P0 Safety Metrics${RESET}`);
  const fpColor = report.false_p0_rate <= 0.05 ? GREEN : report.false_p0_rate <= 0.10 ? YELLOW : RED;
  const mpColor = report.missed_p0_rate <= 0.10 ? GREEN : report.missed_p0_rate <= 0.20 ? YELLOW : RED;
  console.log(`  False-P0 rate   ${fpColor}${pct(report.false_p0_rate)}${RESET}  (system said P0 when expected was not P0)  ${fpColor}target ≤ 5%${RESET}`);
  console.log(`  Missed-P0 rate  ${mpColor}${pct(report.missed_p0_rate)}${RESET}  (expected P0 but system did not assign it)  ${mpColor}target ≤ 10%${RESET}`);

  console.log(`\n${BOLD}Score Distribution${RESET}`);
  const dist = report.score_distribution;
  for (const tier of ['P0', 'P1', 'P2', 'P3', 'P4']) {
    const count = dist[tier] ?? 0;
    const frac  = count / report.total_fixtures;
    console.log(`  ${tierColor(tier)}${tier}${RESET}  ${bar(frac, 15)}  ${count} fixtures  ${pct(frac)}`);
  }

  console.log(`\n${BOLD}Per-Fixture Results${RESET}`);
  console.log(hr);
  for (const r of report.results) {
    printFixtureRow(r);
  }
  console.log(hr);

  const failures = report.results.filter((r) => !r.tier_correct);
  if (failures.length > 0) {
    printFailureAnalysis(failures, report.total_fixtures);
  }

  const passed = report.results.filter((r) => r.tier_correct).length;
  const color  = passed === report.total_fixtures ? GREEN : passed >= report.total_fixtures * 0.8 ? YELLOW : RED;
  console.log(`\n${color}${BOLD}${passed}/${report.total_fixtures} fixtures matched expected tier${RESET}\n`);
}

function printFixtureRow(r: FixtureResult): void {
  const mark     = r.tier_correct ? `${GREEN}✓${RESET}` : `${RED}✗${RESET}`;
  const domainMk = r.domain_correct ? '' : ` ${RED}(domain: got ${r.actual_domain})${RESET}`;
  const tierMk   = r.tier_correct ? '' : ` ${RED}(expected ${r.expected_tier}, got ${r.actual_tier})${RESET}`;

  console.log(`\n  ${mark} ${BOLD}${r.fixture_id}${RESET}${domainMk}${tierMk}`);
  console.log(`     ${DIM}${r.transcript_excerpt}${RESET}`);
  console.log(`     Score: ${r.priority_score?.toFixed(3) ?? '—'}  Tier: ${tierColor(r.actual_tier)}${r.actual_tier ?? '—'}${RESET}  Lang: ${r.language_detected ?? '—'}  Stress: ${r.caller_stress ?? '—'}  Loc: ${(r.location_quality * 100).toFixed(0)}%`);
  if (r.reason_codes.length > 0) {
    console.log(`     Codes: ${DIM}${r.reason_codes.join(', ')}${RESET}`);
  }

  // Show score breakdown inline only for failed tier checks
  if (!r.tier_correct && r.score_breakdown.length > 0) {
    console.log(`     ${YELLOW}Score breakdown (why this score):${RESET}`);
    for (const entry of r.score_breakdown) {
      const sign   = entry.weight >= 0 ? '+' : '';
      const wColor = entry.weight >= 0 ? CYAN : RED;
      console.log(`       ${wColor}${sign}${entry.weight.toFixed(3)}${RESET}  ${entry.reason_code.padEnd(30)}  ${DIM}${entry.description}${RESET}`);
    }
  }
}

function printFailureAnalysis(failures: FixtureResult[], total: number): void {
  const hr = '─'.repeat(72);
  console.log(`\n${BOLD}Failure Analysis${RESET}  ${RED}${failures.length} fixture(s) with incorrect tier${RESET}`);
  console.log(hr);

  // Categorise failures
  const overTriage  = failures.filter((r) => tierRank(r.actual_tier) < tierRank(r.expected_tier));
  const underTriage = failures.filter((r) => tierRank(r.actual_tier) > tierRank(r.expected_tier));
  const domainWrong = failures.filter((r) => !r.domain_correct);

  if (overTriage.length > 0) {
    console.log(`\n  ${RED}Over-triaged (scored too high — ${overTriage.length} fixture(s)):${RESET}`);
    for (const r of overTriage) {
      console.log(`    • ${BOLD}${r.fixture_id}${RESET}  ${r.expected_tier} expected → got ${tierColor(r.actual_tier)}${r.actual_tier}${RESET}  score ${r.priority_score?.toFixed(3) ?? '—'}`);
      const highestContrib = [...r.score_breakdown].sort((a, b) => b.weight - a.weight)[0];
      if (highestContrib) {
        console.log(`      ${DIM}Largest contributor: ${highestContrib.reason_code} (+${highestContrib.weight.toFixed(3)})${RESET}`);
      }
    }
  }

  if (underTriage.length > 0) {
    console.log(`\n  ${RED}Under-triaged (scored too low — ${underTriage.length} fixture(s)):${RESET}`);
    for (const r of underTriage) {
      console.log(`    • ${BOLD}${r.fixture_id}${RESET}  ${r.expected_tier} expected → got ${tierColor(r.actual_tier)}${r.actual_tier}${RESET}  score ${r.priority_score?.toFixed(3) ?? '—'}`);
      const penalties = r.score_breakdown.filter((e) => e.weight < 0);
      if (penalties.length > 0) {
        console.log(`      ${DIM}Penalties applied: ${penalties.map((p) => `${p.reason_code} (${p.weight.toFixed(3)})`).join(', ')}${RESET}`);
      }
    }
  }

  if (domainWrong.length > 0) {
    console.log(`\n  ${YELLOW}Domain misclassification (${domainWrong.length} fixture(s)):${RESET}`);
    for (const r of domainWrong) {
      console.log(`    • ${BOLD}${r.fixture_id}${RESET}  expected domain ${r.expected_domain} → got ${r.actual_domain}`);
    }
  }

  console.log(`\n  ${DIM}${failures.length}/${total} failures  |  over-triaged: ${overTriage.length}  under-triaged: ${underTriage.length}  domain wrong: ${domainWrong.length}${RESET}`);
  console.log(hr);
}

// P0=0, P1=1, ..., P4=4 — lower rank = higher priority
function tierRank(tier: string | null): number {
  const map: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
  return map[tier ?? ''] ?? 99;
}
