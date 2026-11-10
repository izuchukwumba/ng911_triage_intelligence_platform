import { parseTranscript } from '../../transcript-parser/src/parser';
import { scoreIncident } from '../src/scorer';

// Helper: parse a transcript then score it
function triageTranscript(text: string) {
  const record = parseTranscript(text);
  return { record, result: scoreIncident(record) };
}

describe('scoreIncident', () => {
  describe('priority tier assignment', () => {
    it('assigns P0 to a critical life-threatening incident', () => {
      const { result } = triageTranscript(
        'My father is not breathing and has no pulse. Cardiac arrest. We are at 123 Oak Street.',
      );
      expect(result.priority_tier).toBe('P0');
      expect((result.priority_score ?? 0)).toBeGreaterThanOrEqual(0.85);
    });

    it('assigns P0 to a shooting with active bleeding', () => {
      const { result } = triageTranscript(
        'Someone has been shot at 456 Elm Road and is bleeding badly.',
      );
      expect(result.priority_tier).toBe('P0');
    });

    it('assigns P1 or better to active violence without life threat', () => {
      const { result } = triageTranscript(
        'There is a fight and someone is being beaten at 789 Pine Street.',
      );
      expect(['P0', 'P1']).toContain(result.priority_tier);
    });

    it('assigns P3 or lower to a suspicious person welfare check', () => {
      const { result } = triageTranscript(
        'There is a suspicious person near the park. They have been there for about an hour.',
      );
      expect(['P3', 'P4']).toContain(result.priority_tier);
    });

    it('significantly reduces score for prank indicators', () => {
      const { result } = triageTranscript(
        'Never mind, it was a prank call. Just kidding. Ignore this.',
      );
      expect((result.priority_score ?? 0)).toBeLessThan(0.30);
    });
  });

  describe('reason codes', () => {
    it('includes NOT_BREATHING for a respiratory emergency', () => {
      const { result } = triageTranscript('He stopped breathing. Not breathing. No pulse.');
      expect(result.reason_codes).toContain('NOT_BREATHING');
    });

    it('includes WEAPON_PRESENT for a shooting', () => {
      const { result } = triageTranscript('Someone shot him with a gun. He is bleeding.');
      expect(result.reason_codes).toContain('WEAPON_PRESENT');
    });

    it('includes LOW_LOCATION_CONFIDENCE when location is vague', () => {
      const { result } = triageTranscript('Someone is hurt somewhere near here. I do not know the address.');
      expect(result.reason_codes).toContain('LOW_LOCATION_CONFIDENCE');
    });

    it('includes POSSIBLE_PRANK deduction for prank signals', () => {
      const { result } = triageTranscript('prank call, never mind, just kidding');
      expect(result.reason_codes).toContain('POSSIBLE_PRANK');
    });
  });

  describe('score_breakdown', () => {
    it('breakdown entries match reason_codes', () => {
      const { result } = triageTranscript(
        'My mother is not breathing at 123 Oak Street. Cardiac arrest.',
      );
      const breakdownCodes = result.score_breakdown.map((b) => b.reason_code);
      for (const code of result.reason_codes) {
        expect(breakdownCodes).toContain(code);
      }
    });

    it('breakdown weights sum to the clamped final score', () => {
      // score_breakdown now includes the DOMAIN_BASE entry, so the sum of all
      // weights in the breakdown equals the pre-clamp score directly.
      // Do NOT add an extra base offset — that would double-count it.
      const { result } = triageTranscript(
        'There is a fire at 742 Evergreen Terrace and it is spreading.',
      );
      const weightSum = result.score_breakdown.reduce((acc, b) => acc + b.weight, 0);
      const expected = Math.max(0, Math.min(1, weightSum));
      expect(result.priority_score).toBeCloseTo(expected, 2);
    });
  });

  describe('output constraints', () => {
    it('priority_score is always in [0, 1]', () => {
      const transcripts = [
        'Someone was shot and is bleeding badly, cardiac arrest, not breathing at 123 Main St.',
        'hello',
        'prank call never mind',
        'not sure what is happening somewhere',
      ];
      for (const text of transcripts) {
        const { result } = triageTranscript(text);
        expect(result.priority_score).not.toBeNull();
        expect(result.priority_score ?? 0).toBeGreaterThanOrEqual(0);
        expect(result.priority_score ?? 0).toBeLessThanOrEqual(1);
      }
    });

    it('scoring_version is set', () => {
      const { result } = triageTranscript('An emergency is happening.');
      expect(result.scoring_version).toBeTruthy();
    });
  });

  describe('fixture-based acceptance tests', () => {
    const fixtures: Array<{ id: string; text: string; expected_tier: string }> = [
      {
        id: 'fixture-001',
        text: 'Someone has been shot near 5th street and Oak Avenue. There is a lot of blood. He is still conscious but bleeding badly.',
        expected_tier: 'P0',
      },
      {
        id: 'fixture-002',
        text: 'My brother is not breathing at all, please help! We are at 123 Oak Street.',
        expected_tier: 'P0',
      },
      {
        id: 'fixture-009',
        text: 'There is a suspicious person walking around near the school. They have been there for about an hour.',
        expected_tier: 'P3',
      },
    ];

    for (const fixture of fixtures) {
      it(`${fixture.id} scores as ${fixture.expected_tier}`, () => {
        const { result } = triageTranscript(fixture.text);
        expect(result.priority_tier).toBe(fixture.expected_tier);
      });
    }
  });

  // ---------------------------------------------------------------------------
  // Safety invariant: uncertainty never lowers priority
  // ---------------------------------------------------------------------------

  describe('uncertainty does not lower priority', () => {
    const { record } = triageTranscript(
      'My father is not breathing and has no pulse. We are at 123 Oak Street.',
    );
    const baseline = scoreIncident(record);

    it('scores identically when the location is unusable', () => {
      const result = scoreIncident({
        ...record,
        location: { ...record.location, dispatchable_location_score: 0 },
      });
      expect(result.priority_score).toBe(baseline.priority_score);
      expect(result.priority_tier).toBe(baseline.priority_tier);
      expect(result.reason_codes).toContain('LOW_LOCATION_CONFIDENCE');
    });

    it('scores identically when parser confidence is low', () => {
      const result = scoreIncident({
        ...record,
        incident: { ...record.incident, confidence: 0 },
      });
      expect(result.priority_score).toBe(baseline.priority_score);
      expect(result.priority_tier).toBe(baseline.priority_tier);
      expect(result.reason_codes).toContain('LOW_PARSE_CONFIDENCE');
    });

    it('records verification flags with zero weight in the breakdown', () => {
      const result = scoreIncident({
        ...record,
        location: { ...record.location, dispatchable_location_score: 0 },
        incident: { ...record.incident, confidence: 0 },
      });
      const flagWeights = result.score_breakdown
        .filter((b) => ['LOW_LOCATION_CONFIDENCE', 'LOW_PARSE_CONFIDENCE'].includes(b.reason_code))
        .map((b) => b.weight);
      expect(flagWeights).toEqual([0, 0]);
    });
  });

  // ---------------------------------------------------------------------------
  // Edge-case scoring behaviour
  // ---------------------------------------------------------------------------

  describe('edge-case scoring behaviour', () => {
    it('vague location + extreme life-threat still reaches P0 (LOW_LOCATION_CONFIDENCE does not suppress critical incidents)', () => {
      // fixture-011 equivalent: caller doesn't know address but victim is not breathing
      const { result } = triageTranscript(
        "I don't know where I am exactly. Somewhere near downtown. My wife is not breathing. Please hurry.",
      );
      expect(result.priority_tier).toBe('P0');
      expect(result.reason_codes).toContain('NOT_BREATHING');
      expect(result.reason_codes).toContain('LOW_LOCATION_CONFIDENCE');
    });

    it('precise address with minor injury does not inflate priority (fixture-012)', () => {
      const { result } = triageTranscript(
        'I need an ambulance at 2210 West Ridgeway Boulevard apartment 4B. I think I twisted my ankle walking down the stairs.',
      );
      expect(['P3', 'P4']).toContain(result.priority_tier);
      // High dispatchable location score should NOT push tier up
      expect(result.reason_codes).not.toContain('NOT_BREATHING');
      expect(result.reason_codes).not.toContain('CARDIAC_EVENT');
    });

    it('partial address + multiple critical indicators still scores P0 (fixture-023)', () => {
      // Route reference without number — LOW_LOCATION_CONFIDENCE fires but gets overwhelmed
      const { result } = triageTranscript(
        "There's been a multi-car crash on Route 9 near the old overpass. One driver is on the ground, completely unresponsive and not breathing. There is a lot of blood everywhere. I cannot see a street number, just Route 9.",
      );
      expect(result.priority_tier).toBe('P0');
      expect(result.reason_codes).toContain('NOT_BREATHING');
      expect(result.reason_codes).toContain('LOW_LOCATION_CONFIDENCE');
    });

    it('prank call in English reduces score below P3', () => {
      const { result } = triageTranscript(
        'Ha ha relax it was a prank, we were filming a YouTube video. Nobody is actually hurt.',
      );
      expect(result.priority_score ?? 0).toBeLessThan(0.40);
      expect(result.reason_codes).toContain('POSSIBLE_PRANK');
    });

    it('multiple victims increases score via victim count multiplier', () => {
      const singleVictim = triageTranscript('My father collapsed at 456 Elm Road and is not breathing.');
      const multiVictim  = triageTranscript('There are five people injured at the crash at 456 Elm Road. Several are not breathing.');
      expect((multiVictim.result.priority_score ?? 0))
        .toBeGreaterThan((singleVictim.result.priority_score ?? 0));
      expect(multiVictim.result.reason_codes).toContain('MULTIPLE_VICTIMS');
    });

    it('POSSIBLE_PRANK does not suppress score below 0', () => {
      // Score must stay in [0, 1] even with heavy penalty
      const { result } = triageTranscript('prank prank prank prank prank just kidding false alarm disregard');
      expect(result.priority_score ?? 0).toBeGreaterThanOrEqual(0);
      expect(result.priority_score ?? 0).toBeLessThanOrEqual(1);
    });

    it('DOMAIN_BASE entry is always first in score_breakdown', () => {
      const { result } = triageTranscript('Someone has been shot at 123 Main Street. There is a lot of blood.');
      expect(result.score_breakdown[0]?.reason_code).toBe('DOMAIN_BASE');
    });

    it('score_breakdown for a low-severity incident contains only DOMAIN_BASE and possibly verification flags', () => {
      const { result } = triageTranscript(
        'I need an ambulance at 99 Cedar Lane. My elderly neighbour fell and her hip hurts.',
      );
      const positiveIndicatorCodes = result.score_breakdown
        .filter((b) => b.weight > 0 && b.reason_code !== 'DOMAIN_BASE')
        .map((b) => b.reason_code);
      // No severe indicators should have fired
      expect(positiveIndicatorCodes).not.toContain('NOT_BREATHING');
      expect(positiveIndicatorCodes).not.toContain('CARDIAC_EVENT');
      expect(positiveIndicatorCodes).not.toContain('WEAPON_PRESENT');
    });
  });
});
