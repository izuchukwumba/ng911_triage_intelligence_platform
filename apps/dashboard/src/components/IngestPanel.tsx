import { useState } from 'react';
import type { IngestResponse } from '../api/client';
import { api } from '../api/client';

interface Props {
  onIngested: (resp: IngestResponse) => void;
}

const EXAMPLE_TRANSCRIPTS = [
  'My father is not breathing. Cardiac arrest at 123 Oak Street. Please hurry.',
  'Someone has been shot near 5th and Main. There is a lot of blood.',
  'The house at 742 Evergreen Terrace is on fire. The flames are spreading.',
  'Mi hermano no respira. Estamos en 456 Elm Road. Por favor ayúdenos.',
  'There is a suspicious person near the school. They have been there for about an hour.',
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
      const resp = await api.ingest(text.trim());
      onIngested(resp);
      setText('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, fontSize: '13px' }}>Submit Transcript</span>
        <select
          style={{ background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: '4px', fontSize: '11px', padding: '3px 6px', cursor: 'pointer' }}
          value=""
          onChange={(e) => { if (e.target.value) setText(e.target.value); }}
        >
          <option value="">Load example…</option>
          {EXAMPLE_TRANSCRIPTS.map((t, i) => (
            <option key={i} value={t}>{t.slice(0, 50)}…</option>
          ))}
        </select>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter emergency call transcript…"
        rows={3}
        style={{ background: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px 10px', fontSize: '13px', fontFamily: 'var(--mono)', resize: 'vertical', outline: 'none' }}
      />

      {error && <span style={{ color: 'var(--p0)', fontSize: '12px' }}>{error}</span>}

      <button
        type="submit"
        disabled={loading || !text.trim()}
        style={{ alignSelf: 'flex-end', padding: '6px 16px', background: loading ? 'var(--border)' : 'var(--accent)', color: '#0d1117', border: 'none', borderRadius: '6px', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', fontSize: '13px' }}
      >
        {loading ? 'Processing…' : 'Ingest'}
      </button>
    </form>
  );
}
