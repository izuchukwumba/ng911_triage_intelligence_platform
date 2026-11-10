// Always-visible notice required by design v1.2 section 11.2.
export function SimulationBanner() {
  return (
    <div
      role="note"
      aria-label="Simulation notice"
      style={{
        background: 'repeating-linear-gradient(135deg, #3a2a00, #3a2a00 12px, #2c2000 12px, #2c2000 24px)',
        color: '#ffd666',
        fontWeight: 700,
        fontSize: '12px',
        letterSpacing: '0.08em',
        textAlign: 'center',
        padding: '4px 12px',
        flexShrink: 0,
      }}
    >
      SIMULATION — NOT FOR LIVE DISPATCH · synthetic data · advisory output only
    </div>
  );
}
