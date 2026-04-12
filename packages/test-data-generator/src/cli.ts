#!/usr/bin/env node
/**
 * CLI for generating synthetic emergency scenarios.
 *
 * Usage:
 *   ts-node src/cli.ts --count 20 --domain ems --severity critical
 *   ts-node src/cli.ts --count 50 --location-quality mixed --output ../../data/generated/scenarios.json
 */

import { writeFileSync } from 'fs';
import { generateScenarios } from './generator';
import type { GeneratorOptions } from './generator';
import type { IncidentDomain } from '@ng911/incident-schema';

function parseArgs(argv: string[]): GeneratorOptions & { output?: string } {
  const args = argv.slice(2);
  const opts: GeneratorOptions & { output?: string } = {};

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--count':        opts.count = parseInt(args[++i] ?? '10', 10); break;
      case '--domain':       opts.domain = args[++i] as IncidentDomain; break;
      case '--severity':     opts.severity = args[++i] as GeneratorOptions['severity']; break;
      case '--location-quality': opts.locationQuality = args[++i] as GeneratorOptions['locationQuality']; break;
      case '--seed':         opts.seed = parseInt(args[++i] ?? '0', 10); break;
      case '--output':       opts.output = args[++i]; break;
    }
  }

  return opts;
}

const { output, ...generatorOpts } = parseArgs(process.argv);
const scenarios = generateScenarios(generatorOpts);

if (output) {
  writeFileSync(output, JSON.stringify(scenarios, null, 2), 'utf-8');
  console.log(`Generated ${scenarios.length} scenarios → ${output}`);
} else {
  console.log(JSON.stringify(scenarios, null, 2));
}
