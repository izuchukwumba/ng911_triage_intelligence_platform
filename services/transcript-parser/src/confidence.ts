// ---------------------------------------------------------------------------
// Confidence Estimation
// Combines domain classification confidence with evidence strength signals
// to produce an overall parse confidence score for the incident record.
// ---------------------------------------------------------------------------

const HIGH_CONFIDENCE_INDICATORS = new Set([
  'not_breathing',
  'unconscious',
  'weapon_present',
  'active_bleeding',
  'cardiac_event',
  'immediate_medical_emergency',
]);

/**
 * Estimate overall parse confidence.
 *
 * @param domainConfidence  - Confidence from domain classification (0–1)
 * @param severityIndicators - Detected severity indicators
 * @param addressText       - Extracted address, or null
 * @returns                   Overall confidence in the range [0.10, 0.97]
 */
export function estimateConfidence(
  domainConfidence: number,
  severityIndicators: string[],
  addressText: string | null,
): number {
  let score = domainConfidence;

  // High-signal severity indicators increase confidence in classification
  const highSignalCount = severityIndicators.filter((i) =>
    HIGH_CONFIDENCE_INDICATORS.has(i),
  ).length;
  score += Math.min(0.12, highSignalCount * 0.04);

  // Any severity indicator above zero is a positive signal
  if (severityIndicators.length >= 3) score += 0.04;
  if (severityIndicators.length >= 5) score += 0.02;

  // A recovered address adds marginal confidence
  if (addressText) score += 0.04;

  return Math.max(0.10, Math.min(0.97, score));
}
