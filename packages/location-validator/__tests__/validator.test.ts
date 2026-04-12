import { validateLocation } from '../src/validator';

describe('validateLocation', () => {
  describe('no location data', () => {
    it('returns zero scores when address and coordinates are null', () => {
      const result = validateLocation({ address_text: null, lat: null, lng: null });
      expect(result.location_confidence).toBe(0);
      expect(result.dispatchable_location_score).toBe(0);
      expect(result.validation_notes).toContain('no address information provided');
      expect(result.validation_notes).toContain('no dispatchable location — response routing impaired');
    });
  });

  describe('complete address', () => {
    it('scores a numbered street address highly', () => {
      const result = validateLocation({
        address_text: '123 Oak Street',
        lat: null,
        lng: null,
      });
      expect(result.location_confidence).toBeGreaterThan(0.35);
      expect(result.dispatchable_location_score).toBeGreaterThan(0.30);
    });

    it('scores higher when coordinates are also provided', () => {
      const withCoords = validateLocation({ address_text: '123 Oak Street', lat: 40.7, lng: -74.0 });
      const withoutCoords = validateLocation({ address_text: '123 Oak Street', lat: null, lng: null });
      expect(withCoords.location_confidence).toBeGreaterThan(withoutCoords.location_confidence);
    });
  });

  describe('vague address', () => {
    it('penalizes uncertainty language', () => {
      const vague = validateLocation({ address_text: 'near the park somewhere', lat: null, lng: null });
      const clear = validateLocation({ address_text: '123 Oak Street', lat: null, lng: null });
      expect(vague.dispatchable_location_score).toBeLessThan(clear.dispatchable_location_score);
    });
  });

  describe('landmark reference', () => {
    it('gives partial credit for a named landmark', () => {
      const result = validateLocation({
        address_text: 'near the Riverside Hospital',
        lat: null,
        lng: null,
      });
      expect(result.location_confidence).toBeGreaterThan(0.10);
      expect(result.validation_notes).toContain('landmark reference (partial credit)');
    });
  });

  describe('coordinates only', () => {
    it('scores well with coordinates even without address text', () => {
      const result = validateLocation({ address_text: null, lat: 40.7128, lng: -74.0060 });
      expect(result.location_confidence).toBeGreaterThanOrEqual(0.55);
      expect(result.dispatchable_location_score).toBeGreaterThanOrEqual(0.55);
    });
  });

  describe('output constraints', () => {
    it('never returns scores outside [0, 1]', () => {
      const inputs = [
        { address_text: null, lat: null, lng: null },
        { address_text: '123 Oak Street', lat: 40.7, lng: -74.0 },
        { address_text: 'near somewhere vague in the city', lat: null, lng: null },
      ];
      for (const input of inputs) {
        const r = validateLocation(input);
        expect(r.location_confidence).toBeGreaterThanOrEqual(0);
        expect(r.location_confidence).toBeLessThanOrEqual(1);
        expect(r.dispatchable_location_score).toBeGreaterThanOrEqual(0);
        expect(r.dispatchable_location_score).toBeLessThanOrEqual(1);
      }
    });
  });
});
