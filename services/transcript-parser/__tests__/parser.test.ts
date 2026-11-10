import { parseTranscript } from '../src/parser';

describe('parseTranscript', () => {
  describe('domain classification', () => {
    it('classifies a shooting as police domain', () => {
      const record = parseTranscript('Someone has been shot near 5th street. There is blood everywhere.');
      expect(record.incident.domain).toBe('police');
    });

    it('classifies cardiac arrest as ems domain', () => {
      const record = parseTranscript('My father is having a heart attack. He is not breathing at 123 Oak Street.');
      expect(record.incident.domain).toBe('ems');
    });

    it('classifies a house fire as fire domain', () => {
      const record = parseTranscript('The house at 742 Evergreen Terrace is on fire. Flames are coming out of the roof.');
      expect(record.incident.domain).toBe('fire');
    });

    it('classifies a gas leak as hazmat domain', () => {
      const record = parseTranscript('There is a strong chemical smell and a gas leak at 88 Lincoln Drive.');
      expect(record.incident.domain).toBe('hazmat');
    });

    it('returns unknown domain for completely uninformative text', () => {
      const record = parseTranscript('hello there');
      expect(record.incident.domain).toBe('unknown');
    });
  });

  describe('subtype classification', () => {
    it('identifies stabbing subtype', () => {
      const record = parseTranscript('My friend was stabbed with a knife at 456 Elm Road.');
      expect(record.incident.subtype).toBe('stabbing');
    });

    it('identifies respiratory distress subtype', () => {
      const record = parseTranscript('My brother is not breathing. We are at 123 Oak Street.');
      expect(record.incident.subtype).toBe('respiratory_distress');
    });

    it('identifies structure fire subtype', () => {
      const record = parseTranscript('There is a house fire at 350 Fifth Avenue. Flames are spreading.');
      expect(record.incident.subtype).toBe('structure_fire');
    });
  });

  describe('severity indicator extraction', () => {
    it('extracts weapon_present for shooting', () => {
      const record = parseTranscript('Someone was shot with a gun near 5th and Oak.');
      expect(record.incident.severity_indicators).toContain('weapon_present');
    });

    it('extracts not_breathing indicator', () => {
      const record = parseTranscript('He is not breathing and I cannot find a pulse.');
      expect(record.incident.severity_indicators).toContain('not_breathing');
    });

    it('extracts active_bleeding indicator', () => {
      const record = parseTranscript('She is bleeding badly from her chest.');
      expect(record.incident.severity_indicators).toContain('active_bleeding');
    });

    it('extracts child_involved indicator', () => {
      const record = parseTranscript('A child was injured in the car accident on Main Street.');
      expect(record.incident.severity_indicators).toContain('child_involved');
    });

    it('detects possible_prank indicator', () => {
      const record = parseTranscript('Never mind, it was just a prank, ignore this call.');
      expect(record.incident.severity_indicators).toContain('possible_prank');
    });
  });

  describe('address extraction', () => {
    it('extracts a numbered street address', () => {
      const record = parseTranscript('There is an emergency at 123 Oak Street. Please come now.');
      expect(record.location.address_text).toBeTruthy();
      expect(record.location.address_text).toContain('123');
    });

    it('returns null when no address is detectable', () => {
      const record = parseTranscript('Someone is hurt somewhere near here. I do not know the address.');
      expect(record.location.address_text).toBeNull();
    });
  });

  describe('output schema compliance', () => {
    it('always returns a valid UUID incident_id', () => {
      const record = parseTranscript('There is a fire.');
      expect(record.incident_id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
    });

    it('preserves the raw transcript in raw_input.text', () => {
      const text = 'Someone has been shot near 5th street.';
      const record = parseTranscript(text);
      expect(record.raw_input.text).toBe(text);
    });

    it('sets source_type to transcript', () => {
      const record = parseTranscript('Any text');
      expect(record.source_type).toBe('transcript');
    });

    it('leaves triage fields null (populated by scorer)', () => {
      const record = parseTranscript('Any text');
      expect(record.triage.priority_score).toBeNull();
      expect(record.triage.priority_tier).toBeNull();
      expect(record.triage.reason_codes).toHaveLength(0);
    });

    it('confidence is always in [0, 1]', () => {
      const inputs = [
        'hello',
        'Someone has been shot and is bleeding badly at 123 Main Street.',
        'My father is not breathing cardiac arrest 456 Oak Avenue',
      ];
      for (const text of inputs) {
        const { confidence } = parseTranscript(text).incident;
        expect(confidence).toBeGreaterThanOrEqual(0);
        expect(confidence).toBeLessThanOrEqual(1);
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Negation filtering
  // ---------------------------------------------------------------------------

  describe('negation filtering', () => {
    it('does not extract weapon_present when weapon keyword is negated ("no weapon")', () => {
      const record = parseTranscript('Officers searched the vehicle but found no weapon and no contraband.');
      expect(record.incident.severity_indicators).not.toContain('weapon_present');
    });

    it('does not extract weapon_present when negated at close range ("no gun")', () => {
      const record = parseTranscript('I looked around and there was no gun, he was unarmed.');
      expect(record.incident.severity_indicators).not.toContain('weapon_present');
    });

    it('still extracts weapon_present when the weapon is present despite other negation in the sentence', () => {
      // "no injuries" negates nothing related to weapon; weapon_present should fire
      const record = parseTranscript('He had a gun and was threatening people. No injuries so far at 45 Oak Street.');
      expect(record.incident.severity_indicators).toContain('weapon_present');
    });

    it('extracts not_breathing when the phrasing is a direct statement', () => {
      const record = parseTranscript('She stopped breathing completely. She is not breathing.');
      expect(record.incident.severity_indicators).toContain('not_breathing');
    });

    it('does not extract active_bleeding when negated ("no bleeding")', () => {
      const record = parseTranscript('The patient has a wound but there is no bleeding visible at this time.');
      expect(record.incident.severity_indicators).not.toContain('active_bleeding');
    });

    it('does not extract weapon_present when negated by "without"', () => {
      const record = parseTranscript('He walked in without a gun and sat down at 45 Oak Street.');
      expect(record.incident.severity_indicators).not.toContain('weapon_present');
    });

    it('does not extract active_bleeding when the caller "denies" it', () => {
      const record = parseTranscript('She fell down the stairs but denies any bleeding.');
      expect(record.incident.severity_indicators).not.toContain('active_bleeding');
    });

    it('does not extract weapon_present when a multi-word cue negates it ("ruled out")', () => {
      const record = parseTranscript('Police ruled out a gun after searching the car at 45 Oak Street.');
      expect(record.incident.severity_indicators).not.toContain('weapon_present');
    });
  });

  // ---------------------------------------------------------------------------
  // Language detection
  // ---------------------------------------------------------------------------

  describe('language detection', () => {
    it('detects Spanish from high-frequency function words', () => {
      const record = parseTranscript('Mi esposo no está respirando en la Calle Pino 789. Por favor vengan rápido.');
      expect(record.caller_context.language_hint).toBe('es');
    });

    it('detects English for a typical English transcript', () => {
      const record = parseTranscript('My father is not breathing and there is no pulse. We are at 123 Oak Street.');
      expect(record.caller_context.language_hint).toBe('en');
    });

    it('classifies EMS domain correctly for a Spanish cardiac arrest transcript', () => {
      const record = parseTranscript('Mi padre tuvo un ataque al corazón. No respira y no tiene pulso.');
      expect(record.incident.domain).toBe('ems');
    });

    it('extracts not_breathing from a Spanish transcript using ES keyword set', () => {
      const record = parseTranscript('Él no está respirando. Necesito ayuda ahora mismo.');
      expect(record.incident.severity_indicators).toContain('not_breathing');
    });
  });

  // ---------------------------------------------------------------------------
  // Caller stress detection
  // ---------------------------------------------------------------------------

  describe('caller stress detection', () => {
    it('detects high stress from all-caps and word repetition', () => {
      const record = parseTranscript('PLEASE HELP HE IS NOT BREATHING HE IS NOT BREATHING PLEASE COME NOW PLEASE.');
      expect(record.caller_context.caller_stress_level).toBe('high');
    });

    it('detects moderate stress from high-distress phrases', () => {
      const record = parseTranscript('I need help please. He collapsed and I am panicking. Please hurry, please hurry.');
      expect(['moderate', 'high']).toContain(record.caller_context.caller_stress_level);
    });

    it('returns null or low stress for a calm descriptive report', () => {
      const record = parseTranscript('There is a gas leak at 88 Lincoln Drive. We have evacuated the building and are waiting outside.');
      expect(['low', null]).toContain(record.caller_context.caller_stress_level);
    });

    it('CALLER_HIGH_DISTRESS does not suppress other severity indicators', () => {
      // High stress call that also contains a real indicator — both should be present
      const record = parseTranscript('HELP HELP PLEASE MY SON IS NOT BREATHING HELP. We are at 789 Pine Street. PLEASE HURRY.');
      expect(record.incident.severity_indicators).toContain('not_breathing');
      expect(record.caller_context.caller_stress_level).toBe('high');
    });
  });

  // ---------------------------------------------------------------------------
  // Victim count extraction
  // ---------------------------------------------------------------------------

  describe('victim count extraction', () => {
    it('extracts a specific victim count from the transcript', () => {
      const record = parseTranscript('There are four people injured at the scene on Route 9.');
      expect(record.incident.victim_count_estimate).toBeGreaterThanOrEqual(4);
    });

    it('extracts a victim count from range language', () => {
      const record = parseTranscript('I can see at least five or six people on the ground, they look injured.');
      expect(record.incident.victim_count_estimate).toBeGreaterThanOrEqual(4);
    });

    it('returns 1 for single-victim incidents with no count language', () => {
      const record = parseTranscript('My father collapsed and is not breathing at 456 Elm Road.');
      // No multiple-victim language → count should be 1 (or null if not determinable)
      expect(record.incident.victim_count_estimate).toBeLessThanOrEqual(1);
    });

    it('fires multiple_victims indicator when count exceeds one', () => {
      const record = parseTranscript('There are multiple people who were injured. At least three or four people down at 88 Lincoln Drive.');
      expect(record.incident.severity_indicators).toContain('multiple_victims');
    });
  });
});
