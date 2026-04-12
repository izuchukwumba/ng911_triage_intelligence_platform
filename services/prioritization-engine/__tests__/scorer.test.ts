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

    it('all breakdown weights sum to match score (within base offset)', () => {
      const { result } = triageTranscript(
        'There is a fire at 742 Evergreen Terrace and it is spreading.',
      );
      const weightSum = result.score_breakdown.reduce((acc, b) => acc + b.weight, 0);
      // base_score (0.10) + weights = approximately final score
      const expected = Math.max(0, Math.min(1, 0.10 + weightSum));
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
    const fixtures = [
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
});
