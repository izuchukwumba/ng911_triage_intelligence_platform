import type { IncidentDomain } from '@ng911/incident-schema';

// ---------------------------------------------------------------------------
// Scenario templates
//
// Each template is a function that takes a context object and returns a
// transcript string. The context provides variability slots (addresses,
// names, severity language, caller affect).
// ---------------------------------------------------------------------------

export interface TemplateContext {
  address: string;
  callerAffect: string;  // e.g., "panicked", "calm but urgent", "crying"
  extraDetail: string;   // e.g., "He's not moving at all.", ""
}

export interface ScenarioTemplate {
  domain: IncidentDomain;
  subtype: string;
  severity: 'critical' | 'high' | 'moderate' | 'low';
  generate: (ctx: TemplateContext) => string;
}

export const SCENARIO_TEMPLATES: ScenarioTemplate[] = [
  // -------------------------------------------------------------------------
  // Police — Shooting
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'shooting',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `Someone's been shot at ${address}. There's blood everywhere. ${extraDetail} Please hurry!`,
  },
  {
    domain: 'police',
    subtype: 'shooting',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `I just heard gunshots near ${address} and I can see a person lying on the ground. ${extraDetail} Send police now.`,
  },

  // -------------------------------------------------------------------------
  // Police — Stabbing
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'stabbing',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `My friend has been stabbed at ${address}. He's bleeding badly. ${extraDetail} We need an ambulance too.`,
  },

  // -------------------------------------------------------------------------
  // Police — Domestic Violence
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'domestic_violence',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `My neighbor is fighting with her husband at ${address} and I heard screaming. ${extraDetail} I think she's being hurt.`,
  },

  // -------------------------------------------------------------------------
  // Police — Robbery
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'robbery',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `Someone just robbed me at ${address}. He had a gun. ${extraDetail} He ran east down the street.`,
  },

  // -------------------------------------------------------------------------
  // Fire — Structure fire
  // -------------------------------------------------------------------------
  {
    domain: 'fire',
    subtype: 'structure_fire',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `The house at ${address} is on fire. The flames are coming out of the second floor windows and spreading. ${extraDetail} People might still be inside.`,
  },
  {
    domain: 'fire',
    subtype: 'structure_fire',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `I can see smoke coming from the building at ${address}. ${extraDetail} It looks like a fire in the kitchen.`,
  },

  // -------------------------------------------------------------------------
  // Fire — Gas leak
  // -------------------------------------------------------------------------
  {
    domain: 'fire',
    subtype: 'gas_leak',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `There's a strong smell of gas at ${address}. ${extraDetail} We evacuated the building but I don't know if everyone got out.`,
  },

  // -------------------------------------------------------------------------
  // EMS — Cardiac
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'cardiac_arrest',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `My father just collapsed at ${address}. He's not breathing and I can't find a pulse. ${extraDetail} I don't know how to do CPR.`,
  },
  {
    domain: 'ems',
    subtype: 'cardiac_arrest',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `My husband is having a heart attack at ${address}. He's unconscious and not breathing. ${extraDetail} Please send an ambulance immediately.`,
  },

  // -------------------------------------------------------------------------
  // EMS — Respiratory distress
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'respiratory_distress',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `My brother is not breathing, please help! We are at ${address}. ${extraDetail} He was fine and then just stopped breathing.`,
  },
  {
    domain: 'ems',
    subtype: 'respiratory_distress',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `My wife is having difficulty breathing at ${address}. ${extraDetail} She's conscious but gasping. She has asthma.`,
  },

  // -------------------------------------------------------------------------
  // EMS — Trauma
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'trauma',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `There's been a car accident at ${address}. Two vehicles involved. ${extraDetail} One person is trapped and bleeding.`,
  },
  {
    domain: 'ems',
    subtype: 'trauma',
    severity: 'moderate',
    generate: ({ address, extraDetail }) =>
      `An elderly woman fell on the sidewalk near ${address}. ${extraDetail} She can't get up and says her hip hurts badly.`,
  },

  // -------------------------------------------------------------------------
  // EMS — Overdose
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'overdose',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `My roommate overdosed at ${address}. He's unresponsive and won't wake up. ${extraDetail} I think he took something.`,
  },

  // -------------------------------------------------------------------------
  // EMS — Seizure
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'seizure',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `My son is having a seizure at ${address}. ${extraDetail} It's been going on for over two minutes and he won't stop.`,
  },

  // -------------------------------------------------------------------------
  // Hazmat — Gas leak
  // -------------------------------------------------------------------------
  {
    domain: 'hazmat',
    subtype: 'gas_leak',
    severity: 'high',
    generate: ({ address, extraDetail }) =>
      `There's a chemical smell coming from the building at ${address}. ${extraDetail} Several people are complaining of headaches and dizziness.`,
  },

  // -------------------------------------------------------------------------
  // Low severity / welfare check
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'suspicious_person',
    severity: 'low',
    generate: ({ address, extraDetail }) =>
      `There's a suspicious person walking around ${address}. ${extraDetail} They've been there for about an hour.`,
  },
  {
    domain: 'ems',
    subtype: 'unconscious_unknown',
    severity: 'moderate',
    generate: ({ address, extraDetail }) =>
      `There's a person slumped over on the bench near ${address}. ${extraDetail} I don't know if they're sleeping or something is wrong.`,
  },

  // -------------------------------------------------------------------------
  // Uncertain / hedged weapon mention
  //
  // Tests whether the parser fires weapon_present from ambiguous phrasing.
  // Current behaviour: weapon_present fires (keyword match is not
  // uncertainty-aware). Expectation: P2 at most.
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'suspicious_person',
    severity: 'moderate',
    generate: ({ address, extraDetail }) =>
      `Someone threatening near ${address}. I think he might have had a gun or something in his jacket — I couldn't clearly see. ${extraDetail} He left the area.`,
  },

  // -------------------------------------------------------------------------
  // False alarm / retraction
  //
  // Caller explicitly retracts the emergency report. Known gap: the parser
  // may still score weapon_present from words like "gunshots" before
  // seeing the retraction. Documents the need for retraction-aware parsing.
  // -------------------------------------------------------------------------
  {
    domain: 'police',
    subtype: 'unclassified',
    severity: 'low',
    generate: ({ address, extraDetail }) =>
      `Sorry, false alarm near ${address} — I thought I heard gunshots but it was just a car backfiring. ${extraDetail} Nobody is hurt, disregard.`,
  },

  // -------------------------------------------------------------------------
  // Partial address with high severity
  //
  // Route or intersection reference without a building number. Expected to
  // trigger LOW_LOCATION_CONFIDENCE but still score P0 when multiple
  // life-threat indicators are present.
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'trauma',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `Bad crash on ${address} near the overpass. One driver is on the ground, unresponsive and not breathing. ${extraDetail} There is blood everywhere. No street number visible.`,
  },

  // -------------------------------------------------------------------------
  // High-stress overwhelmed caller
  //
  // Extreme affect: repetition, fragmentation, caps-style phrasing.
  // Caller stress detection should flag HIGH. Used to test that stress
  // signals add CALLER_HIGH_DISTRESS without incorrectly suppressing
  // other indicator extraction.
  // -------------------------------------------------------------------------
  {
    domain: 'ems',
    subtype: 'respiratory_distress',
    severity: 'critical',
    generate: ({ address, extraDetail }) =>
      `PLEASE HELP PLEASE HELP. He is not breathing he is not breathing. We are at ${address}. ${extraDetail} PLEASE COME NOW PLEASE.`,
  },
];
