import { useState } from 'react';
import type { IngestOut } from '../api/client';
import { api } from '../api/client';

interface Props {
  onIngested: (result: IngestOut) => void;
}

// All examples are synthetic.
const EXAMPLE_TRANSCRIPTS = [
  'My father is not breathing. We are in apartment 4B at 12 Oak Street. Please hurry.',
  'Someone has been shot near 5th and Main. There is a lot of blood.',
  "My wife is not breathing. I don't know where I am, somewhere near downtown.",
  'I think I heard a gunshot near the Riverside park.',
  'There is smoke coming from the second floor and people are trapped inside.',
  'Mi hermano no respira. Estamos en la Calle Pino 789. Por favor ayúdenos.',
  'Never mind, it was just a prank, ignore this call.',
];

export function IngestPanel({ onIngested }: Props) {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    try {
      onIngested(await api.ingest(text.trim()));
      setText('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} aria-label="Submit synthetic transcript" style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <label htmlFor="transcript" style={{ fontWeight: 600, fontSize: '13px' }}>Synthetic transcript</label>
        <select
          aria-label="Load an example transcript"
          style={{ background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '11px', padding: '3px 6px' }}
          value=""
          onChange={(e) => { if (e.target.value) setText(e.target.value); }}
        >
          <option value="">Load example…</option>
          {EXAMPLE_TRANSCRIPTS.map((t) => <option key={t} value={t}>{t.slice(0, 50)}…</option>)}
        </select>
      </div>
      <textarea
        id="transcript"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type or load a synthetic emergency-call transcript…"
        rows={3}
        style={{ background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px 10px', fontSize: '13px', fontFamily: 'var(--mono)', resize: 'vertical' }}
      />
      {error && <span role="alert" style={{ color: 'var(--p0)', fontSize: '12px' }}>{error}</span>}
      <button type="submit" className="btn btn-primary" disabled={loading || !text.trim()} style={{ alignSelf: 'flex-end' }}>
        {loading ? 'Processing…' : 'Submit'}
      </button>
    </form>
  );
}
