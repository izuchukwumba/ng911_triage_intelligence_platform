import { z } from 'zod';

// ---------------------------------------------------------------------------
// Sub-schemas
// ---------------------------------------------------------------------------

export const RawInputSchema = z.object({
  text: z.string(),
  audio_url: z.string().url().nullable().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const IncidentDomainSchema = z.enum([
  'police',
  'fire',
  'ems',
  'hazmat',
  'other',
  'unknown',
]);

export const IncidentCoreSchema = z.object({
  domain: IncidentDomainSchema,
  subtype: z.string(),
  summary: z.string(),
  severity_indicators: z.array(z.string()),
  victim_count_estimate: z.number().int().positive().nullable(),
  confidence: z.number().min(0).max(1),
});

export const LocationSchema = z.object({
  address_text: z.string().nullable(),
  lat: z.number().min(-90).max(90).nullable(),
  lng: z.number().min(-180).max(180).nullable(),
  location_confidence: z.number().min(0).max(1),
  dispatchable_location_score: z.number().min(0).max(1),
  validation_notes: z.array(z.string()),
});

export const NoiseLevel = z.enum(['low', 'moderate', 'high']);
export const StressLevel = z.enum(['low', 'moderate', 'high']);

export const CallerContextSchema = z.object({
  caller_id_hash: z.string().nullable(),
  language_hint: z.string().nullable(),
  background_noise_level: NoiseLevel.nullable(),
  caller_stress_level: StressLevel.nullable(),
});

export type StressLevelValue = z.infer<typeof StressLevel>;

export const PriorityTierSchema = z.enum(['P0', 'P1', 'P2', 'P3', 'P4']);

export const TriageSchema = z.object({
  priority_score: z.number().min(0).max(1).nullable(),
  priority_tier: PriorityTierSchema.nullable(),
  reason_codes: z.array(z.string()),
});

export const AuditSchema = z.object({
  schema_version: z.string(),
  parser_version: z.string().nullable(),
  scoring_version: z.string().nullable(),
  processed_at: z.string().datetime().nullable(),
});

// ---------------------------------------------------------------------------
// Top-level incident record
// ---------------------------------------------------------------------------

export const IncidentRecordSchema = z.object({
  incident_id: z.string().uuid(),
  received_at: z.string().datetime(),
  source_type: z.enum(['transcript', 'json', 'api', 'simulation']),
  raw_input: RawInputSchema,
  incident: IncidentCoreSchema,
  location: LocationSchema,
  caller_context: CallerContextSchema,
  triage: TriageSchema,
  audit: AuditSchema,
});

// ---------------------------------------------------------------------------
// Inferred TypeScript types
// ---------------------------------------------------------------------------

export type RawInput = z.infer<typeof RawInputSchema>;
export type IncidentCore = z.infer<typeof IncidentCoreSchema>;
export type Location = z.infer<typeof LocationSchema>;
export type CallerContext = z.infer<typeof CallerContextSchema>;
export type Triage = z.infer<typeof TriageSchema>;
export type Audit = z.infer<typeof AuditSchema>;
export type IncidentRecord = z.infer<typeof IncidentRecordSchema>;

export type IncidentDomain = z.infer<typeof IncidentDomainSchema>;
export type PriorityTier = z.infer<typeof PriorityTierSchema>;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const SCHEMA_VERSION = '0.2.0';

export const PRIORITY_TIER_LABELS: Record<PriorityTier, string> = {
  P0: 'IMMEDIATE — Life-threatening',
  P1: 'URGENT — High severity',
  P2: 'ELEVATED — Moderate severity',
  P3: 'STANDARD — Low to moderate severity',
  P4: 'NON-URGENT — Monitor or defer',
};
