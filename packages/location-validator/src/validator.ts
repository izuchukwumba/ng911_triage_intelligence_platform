export interface LocationInput {
  address_text: string | null;
  lat: number | null;
  lng: number | null;
}

export interface LocationValidation {
  location_confidence: number;
  dispatchable_location_score: number;
  validation_notes: string[];
}

// Patterns that indicate a properly formed, dispatchable address
const COMPLETE_ADDRESS_PATTERNS = [
  // Numbered street: "123 Oak Street", "456 N Main Ave"
  /\b\d+\s+(?:[NSEW]\s+)?[\w]+(?:\s+[\w]+)?\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|way|court|ct|place|pl|circle|cir|highway|hwy|parkway|pkwy|terrace|ter|trail|trl)\b/i,
  // Intersection reference: "5th and Oak", "Main and Elm Street"
  /\b[\w]+(?:\s+[\w]+)?\s+(?:and|&)\s+[\w]+(?:\s+[\w]+)?(?:\s+(?:street|st|avenue|ave|road|rd|blvd))?/i,
];

// Patterns that reduce confidence — vague spatial references
const VAGUE_LOCATION_PATTERNS = [
  /\bnear\b/i,
  /\baround\b/i,
  /\bsomewhere\b/i,
  /\bnearby\b/i,
  /\bby the\b/i,
  /\bnot sure\b/i,
  /\bdon'?t know(?: the address)?\b/i,
];

// Patterns that suggest a known named place (partial credit)
const LANDMARK_PATTERNS = [
  /\b[\w\s]{3,40}(?:park|school|hospital|mall|plaza|center|centre|station|church|clinic|intersection|corner)\b/i,
];

function clamp(value: number): number {
  return Math.max(0, Math.min(1, value));
}

export function validateLocation(input: LocationInput): LocationValidation {
  const notes: string[] = [];
  let confidence = 0;
  let dispatchable = 0;

  // Coordinates provide highest-quality location signal
  if (input.lat !== null && input.lng !== null) {
    confidence += 0.55;
    dispatchable += 0.60;
    notes.push('coordinates present');
  }

  if (input.address_text) {
    const text = input.address_text;
    const isComplete = COMPLETE_ADDRESS_PATTERNS.some((p) => p.test(text));
    const isVague = VAGUE_LOCATION_PATTERNS.some((p) => p.test(text));
    const isLandmark = LANDMARK_PATTERNS.some((p) => p.test(text));

    if (isComplete) {
      confidence += 0.40;
      dispatchable += 0.38;
    } else if (isLandmark) {
      confidence += 0.20;
      dispatchable += 0.15;
      notes.push('landmark reference (partial credit)');
    } else {
      confidence += 0.10;
      dispatchable += 0.05;
      notes.push('address incomplete or unrecognized');
    }

    if (isVague) {
      confidence -= 0.15;
      dispatchable -= 0.22;
      notes.push('uncertainty language detected in address');
    }

    // Cross-street intersection adds slight confidence
    if (/\b(?:and|&|intersection of|corner of)\b/i.test(text)) {
      confidence += 0.05;
      dispatchable += 0.04;
    }

    // ZIP code presence
    if (/\b\d{5}(?:-\d{4})?\b/.test(text)) {
      confidence += 0.04;
      notes.push('ZIP code present');
    }
  } else {
    notes.push('no address information provided');
  }

  if (!input.address_text && input.lat === null) {
    notes.push('no dispatchable location — response routing impaired');
  }

  return {
    location_confidence: clamp(confidence),
    dispatchable_location_score: clamp(dispatchable),
    validation_notes: notes,
  };
}
