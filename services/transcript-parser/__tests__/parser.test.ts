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
});
