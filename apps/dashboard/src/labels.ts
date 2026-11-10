// Human-readable text for machine codes. Every coloured element in the UI is
// paired with one of these labels, so no information depends on colour alone.

export const PRIORITY_LABELS: Record<string, string> = {
  P0: 'Immediate',
  P1: 'Urgent',
  P2: 'Elevated',
  P3: 'Standard',
  P4: 'Low',
};

export const SEVERITY_LABELS: Record<string, string> = {
  critical: 'Critical',
  high: 'High',
  elevated: 'Elevated',
  standard: 'Standard',
  low: 'Low',
  undetermined: 'Undetermined',
};

export const REVIEW_ACTION_LABELS: Record<string, string> = {
  URGENT_HUMAN_REVIEW: 'Urgent human review — processing failed',
  CONFIRM_CRITICAL_REPORT: 'Confirm the critical report with the caller',
  VERIFY_LOCATION: 'Verify the location',
  CONFIRM_CLASSIFICATION: 'Confirm what kind of incident this is',
  RESOLVE_CONFLICT: 'Resolve contradictory statements',
};

export const STATE_LABELS: Record<string, string> = {
  awaiting_review: 'Awaiting review',
  reviewed: 'Reviewed',
  processing_failed: 'Processing failed',
  closed: 'Closed',
};

export const LOCATION_QUALITY_LABELS: Record<string, string> = {
  sufficient: 'Verified',
  requires_verification: 'Needs verification',
  missing: 'No location',
  conflicting: 'Conflicting locations',
};

export const POLARITY_LABELS: Record<string, string> = {
  affirmed: 'stated',
  negated: 'denied',
  uncertain: 'uncertain',
};

export function codeLabel(code: string): string {
  const words = code.toLowerCase().split('_').join(' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function priorityColor(priority: string | null | undefined): string {
  return priority ? `var(--${priority.toLowerCase()})` : 'var(--text-muted)';
}
