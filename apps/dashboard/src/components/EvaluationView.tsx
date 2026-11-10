import { useCallback, useEffect, useState } from 'react';
import type { DatasetName, EvaluationReport, ReportSplit } from '../api/client';
import { api } from '../api/client';

type Rate = EvaluationReport['metrics']['priority_exact'];

// Evaluation report (design v1.2, section 11.1): metrics, dataset details,
// failed cases, version pins and exports. The server evaluates the deployed
// rules baseline on the dev and regression splits only; the held-out test
// split is never browsed here.
const RATES: { key: keyof EvaluationReport['metrics']; label: string; lowerIsBetter?: boolean }[] = [
  { key: 'critical_cue_sensitivity', label: 'Critical-cue sensitivity' },
  { key: 'critical_undertriage', label: 'Critical under-triage (expected P0, predicted lower)', lowerIsBetter: true },
  { key: 'priority_exact', label: 'Priority exact agreement' },
  { key: 'undertriage', label: 'Under-triage (any)', lowerIsBetter: true },
  { key: 'overtriage', label: 'Over-triage (any)', lowerIsBetter: true },
  { key: 'severity_exact', label: 'Severity band exact' },
  { key: 'domain_accuracy', label: 'Domain accuracy' },
  { key: 'location_accuracy', label: 'Location status accuracy' },
  { key: 'victim_count_accuracy', label: 'Victim count accuracy' },
];
const PRIORITIES = ['P0', 'P1', 'P2', 'P3', 'P4', 'none'];

function fmt(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(3);
}

function download(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function EvaluationView() {
  const [dataset, setDataset] = useState<DatasetName>('curated');
  const [splits, setSplits] = useState<ReportSplit[]>(['dev', 'regression']);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setReport(await api.evaluationReport(dataset, splits));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }, [dataset, splits]);

  useEffect(() => {
    void load();
  }, [load]);

  function toggle(split: ReportSplit) {
    setSplits((current) => {
      const next = current.includes(split) ? current.filter((s) => s !== split) : [...current, split];
      return next.length ? next : current; // at least one split
    });
  }

  const name = `b0-${dataset}-${splits.join('-')}`;

  async function exportMarkdown() {
    try {
      download(`${name}.md`, await api.evaluationMarkdown(dataset, splits), 'text/markdown');
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <section aria-labelledby="evaluation-title" style={{ padding: '16px 24px', overflowY: 'auto', height: '100%', display: 'grid', gap: '12px', alignContent: 'start' }}>
      <h2 id="evaluation-title" style={{ fontSize: '15px' }}>Evaluation report · rules baseline (B0)</h2>
      <div className="panel" style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
        <label style={{ fontSize: '13px' }}>
          Dataset{' '}
          <select className="input" value={dataset} onChange={(e) => setDataset(e.target.value as DatasetName)}>
            <option value="curated">Curated (hand-written)</option>
            <option value="generated">Generated (stress set)</option>
          </select>
        </label>
        <fieldset style={{ border: 'none', display: 'flex', gap: '10px', fontSize: '13px' }}>
          <legend className="muted" style={{ float: 'left', marginRight: '6px' }}>Splits</legend>
          {(['dev', 'regression'] as ReportSplit[]).map((split) => (
            <label key={split}>
              <input type="checkbox" checked={splits.includes(split)} onChange={() => toggle(split)} /> {split}
            </label>
          ))}
        </fieldset>
        <span className="muted" style={{ fontSize: '12px' }}>The held-out test split is not shown here.</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '6px' }}>
          <button type="button" className="btn" onClick={() => void exportMarkdown()} disabled={!report}>Export Markdown</button>
          <button type="button" className="btn" disabled={!report}
            onClick={() => report && download(`${name}.json`, JSON.stringify(report, null, 2), 'application/json')}>
            Export JSON
          </button>
        </div>
      </div>

      {busy && <p role="status" className="muted">Evaluating…</p>}
      {error && <p role="alert" style={{ color: 'var(--p0)' }}>{error}</p>}

      {report && (
        <>
          <p role="note" className="panel" style={{ fontSize: '12px' }}>⚠ {report.note}</p>

          <div className="panel">
            <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
              <caption className="section-title" style={{ textAlign: 'left' }}>Metrics ({report.metrics.cases} cases, 95% bootstrap intervals)</caption>
              <thead>
                <tr className="muted" style={{ textAlign: 'left' }}>
                  <th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Count</th><th scope="col">95% CI</th>
                </tr>
              </thead>
              <tbody>
                {RATES.map(({ key, label, lowerIsBetter }) => {
                  const rate = report.metrics[key] as Rate;
                  return (
                    <tr key={key}>
                      <th scope="row" style={{ fontWeight: 400, textAlign: 'left' }}>
                        {label}{lowerIsBetter && <span className="muted"> (lower is better)</span>}
                      </th>
                      <td className="mono">{fmt(rate.value)}</td>
                      <td className="mono">{rate.numerator}/{rate.denominator}</td>
                      <td className="mono">{rate.ci95 ? `${fmt(rate.ci95[0])} – ${fmt(rate.ci95[1])}` : '—'}</td>
                    </tr>
                  );
                })}
                <tr>
                  <th scope="row" style={{ fontWeight: 400, textAlign: 'left' }}>Cue extraction precision / recall / F1</th>
                  <td className="mono" colSpan={2}>
                    {fmt(report.metrics.cue_extraction.precision)} / {fmt(report.metrics.cue_extraction.recall)} / {fmt(report.metrics.cue_extraction.f1)}
                  </td>
                  <td className="mono">F1 {fmt(report.metrics.cue_extraction.f1_ci95[0])} – {fmt(report.metrics.cue_extraction.f1_ci95[1])}</td>
                </tr>
                <tr>
                  <th scope="row" style={{ fontWeight: 400, textAlign: 'left' }}>Denied or past cues treated as live</th>
                  <td className="mono" colSpan={3}>{report.metrics.cue_extraction.denied_or_past_cues_treated_as_live}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="panel">
            <table style={{ fontSize: '13px', borderCollapse: 'collapse' }}>
              <caption className="section-title" style={{ textAlign: 'left' }}>Priority confusion (rows: expected, columns: predicted)</caption>
              <thead>
                <tr><td />{PRIORITIES.map((p) => <th key={p} scope="col">{p}</th>)}</tr>
              </thead>
              <tbody>
                {PRIORITIES.map((expected) => (
                  <tr key={expected}>
                    <th scope="row">{expected}</th>
                    {PRIORITIES.map((predicted) => {
                      const n = report.metrics.priority_confusion[expected]?.[predicted] ?? 0;
                      return (
                        <td key={predicted} className="mono" style={{ textAlign: 'center', fontWeight: expected === predicted ? 700 : 400 }}>
                          {n}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <h3 className="section-title">Failed cases ({report.failed_cases.length})</h3>
            {report.failed_cases.length === 0 ? (
              <p style={{ fontSize: '13px' }}>Every case matched its labels.</p>
            ) : (
              <ul style={{ listStyle: 'none', display: 'grid', gap: '8px' }}>
                {report.failed_cases.map((c) => (
                  <li key={c.case_id} style={{ borderLeft: `3px solid ${c.critical ? 'var(--p0)' : 'var(--border)'}`, paddingLeft: '8px', fontSize: '13px' }}>
                    <div>
                      <span className="mono">{c.case_id}</span> <span className="muted">· {c.split} · expected {c.expected_priority ?? '—'}</span>
                      {c.critical && <strong style={{ color: 'var(--p0)' }}> · ⚠ critical case</strong>}
                    </div>
                    <blockquote className="muted" style={{ margin: '2px 0' }}>{c.messages.join(' / ')}</blockquote>
                    <ul style={{ paddingLeft: '18px' }}>{c.errors.map((e) => <li key={e} className="mono" style={{ fontSize: '12px' }}>{e}</li>)}</ul>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="panel">
            <h3 className="section-title">Version pins (reproduce this report)</h3>
            <dl style={{ display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '2px 12px', fontSize: '12px' }}>
              {([
                ['System', report.pins.system],
                ['Dataset', `${report.pins.dataset_path} (${report.pins.splits.join(', ')})`],
                ['Dataset digest', report.pins.dataset_digest],
                ['Parser / engine', `${report.pins.parser} / ${report.pins.engine}`],
                ['Ruleset', `${report.pins.ruleset} (${report.pins.ruleset_digest})`],
                ['Schema', report.pins.schema_version],
                ['Git commit', report.pins.git_commit],
                ['Python / lockfile', `${report.pins.python} / ${report.pins.lockfile_digest ?? 'not available'}`],
                ['Seed / bootstrap', `${report.pins.seed} / ${report.pins.bootstrap}`],
              ] as const).map(([term, value]) => (
                <div key={term} style={{ display: 'contents' }}>
                  <dt className="muted">{term}</dt>
                  <dd className="mono" style={{ wordBreak: 'break-all' }}>{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </>
      )}
    </section>
  );
}
