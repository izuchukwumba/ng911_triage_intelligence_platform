#!/usr/bin/env node
/**
 * Evaluation CLI
 *
 * Usage:
 *   ts-node src/cli.ts
 *   ts-node src/cli.ts --fixtures ../../data/fixtures/sample-incidents.json
 *   ts-node src/cli.ts --output eval-results.json
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';
import { buildReport } from './harness';
import { printReport } from './report';
import type { Fixture } from './types';

function parseArgs() {
  const args = process.argv.slice(2);
  let fixturesPath = resolve(__dirname, '../../../data/fixtures/sample-incidents.json');
  let outputPath: string | null = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--fixtures' && args[i + 1]) fixturesPath = resolve(args[++i]);
    if (args[i] === '--output'   && args[i + 1]) outputPath   = resolve(args[++i]);
  }

  return { fixturesPath, outputPath };
}

const { fixturesPath, outputPath } = parseArgs();

let rawFixtures: unknown[];
try {
  rawFixtures = JSON.parse(readFileSync(fixturesPath, 'utf-8')) as unknown[];
} catch (e) {
  console.error(`Failed to load fixtures from ${fixturesPath}: ${(e as Error).message}`);
  process.exit(1);
}

// Normalise fixture shape (handles both the data/fixtures format and
// the test-data-generator output format)
const fixtures: Fixture[] = rawFixtures.map((raw, i) => {
  const r = raw as Record<string, unknown>;
  return {
    id:                     String(r['id'] ?? `fixture-${i + 1}`),
    transcript:             String(r['transcript'] ?? r['text'] ?? ''),
    expected_domain:        String(r['expected_domain'] ?? 'unknown'),
    expected_subtype:       String(r['expected_subtype'] ?? 'unclassified'),
    expected_priority_tier: String(r['expected_priority_tier'] ?? r['expected_tier'] ?? 'P4'),
    severity:               String(r['severity'] ?? r['expected_severity'] ?? 'unknown'),
    notes:                  r['notes'] ? String(r['notes']) : undefined,
  };
}).filter((f) => f.transcript.length > 0);

if (fixtures.length === 0) {
  console.error('No valid fixtures found. Each fixture must have a `transcript` field.');
  process.exit(1);
}

const report = buildReport(fixtures);
printReport(report);

if (outputPath) {
  writeFileSync(outputPath, JSON.stringify(report, null, 2), 'utf-8');
  console.log(`Report saved to ${outputPath}`);
}
