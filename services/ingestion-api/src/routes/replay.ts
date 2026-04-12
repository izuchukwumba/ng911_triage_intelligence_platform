import { Router } from 'express';
import { parseTranscript } from '@ng911/transcript-parser';
import { scoreIncident } from '@ng911/prioritization-engine';
import { getStore } from '../store';

export const replayRouter = Router();

/**
 * POST /replay/:id
 *
 * Re-parse and re-score a stored incident from its original raw_input.
 * Returns the new result alongside the stored original for comparison.
 *
 * This is the foundation of the audit/replay workflow — allows operators
 * to evaluate how a scoring config change would affect past incidents.
 */
// ---------------------------------------------------------------------------
// POST /replay/stream  — batch replay comparison
// ---------------------------------------------------------------------------

/**
 * POST /replay/stream
 *
 * Re-parse and re-score multiple stored incidents in one call.
 * Returns an array of per-incident comparison objects plus aggregate stats.
 *
 * Useful for evaluating how a scoring config change would affect a set of
 * incidents (e.g., all P0 incidents from the past week).
 *
 * Body: { "incident_ids": ["uuid1", "uuid2", ...] }
 *       Pass "all" to replay every stored incident.
 */
replayRouter.post('/stream', (req, res, next) => {
  try {
    const { incident_ids } = req.body as { incident_ids?: unknown };

    const store = getStore();

    let ids: string[];
    if (incident_ids === 'all') {
      ids = store.findAll({ limit: 500 }).incidents.map((i) => i.incident_id);
    } else if (Array.isArray(incident_ids)) {
      ids = incident_ids.filter((id): id is string => typeof id === 'string');
    } else {
      res.status(400).json({ error: '`incident_ids` must be an array of UUIDs or the string "all"' });
      return;
    }

    if (ids.length === 0) {
      res.status(400).json({ error: 'No incident IDs provided' });
      return;
    }

    if (ids.length > 200) {
      res.status(400).json({ error: 'Maximum 200 incidents per stream replay request' });
      return;
    }

    const results = [];
    let tierChanged = 0;
    let scoreImproved = 0;
    let scoreDegraded = 0;

    for (const id of ids) {
      const original = store.findById(id);
      if (!original) {
        results.push({ incident_id: id, error: 'not found' });
        continue;
      }

      const replayed = parseTranscript(original.raw_input.text);
      const scoring = scoreIncident(replayed);

      const replayedRecord = {
        ...replayed,
        incident_id: original.incident_id,
        triage: {
          priority_score: scoring.priority_score,
          priority_tier: scoring.priority_tier,
          reason_codes: scoring.reason_codes,
        },
        audit: { ...replayed.audit, scoring_version: scoring.scoring_version },
      };

      const scoreDelta =
        (scoring.priority_score ?? 0) - (original.triage.priority_score ?? 0);
      const changed = original.triage.priority_tier !== scoring.priority_tier;

      if (changed) tierChanged++;
      if (scoreDelta > 0.01) scoreImproved++;
      if (scoreDelta < -0.01) scoreDegraded++;

      results.push({
        incident_id: id,
        original_tier: original.triage.priority_tier,
        replayed_tier: scoring.priority_tier,
        score_delta: Math.round(scoreDelta * 1000) / 1000,
        tier_changed: changed,
        reason_codes_added: scoring.reason_codes.filter(
          (c) => !original.triage.reason_codes.includes(c),
        ),
        reason_codes_removed: original.triage.reason_codes.filter(
          (c) => !scoring.reason_codes.includes(c),
        ),
        replayed_record: replayedRecord,
        score_breakdown: scoring.score_breakdown,
      });
    }

    res.json({
      total_replayed: results.length,
      summary: { tier_changed: tierChanged, score_improved: scoreImproved, score_degraded: scoreDegraded },
      results,
    });
  } catch (err) {
    next(err);
  }
});

// ---------------------------------------------------------------------------
// POST /replay/:id  — single incident replay
// ---------------------------------------------------------------------------

replayRouter.post('/:id', (req, res, next) => {
  try {
    const store = getStore();
    const original = store.findById(req.params['id'] ?? '');

    if (!original) {
      res.status(404).json({ error: `Incident ${req.params['id']} not found` });
      return;
    }

    const replayed = parseTranscript(original.raw_input.text);
    const { priority_score, priority_tier, reason_codes, scoring_version, score_breakdown } =
      scoreIncident(replayed);

    const replayedRecord = {
      ...replayed,
      incident_id: original.incident_id,
      triage: { priority_score, priority_tier, reason_codes },
      audit: {
        ...replayed.audit,
        scoring_version,
      },
    };

    res.json({
      original,
      replayed: replayedRecord,
      score_breakdown,
      diff: {
        priority_tier_changed:
          original.triage.priority_tier !== replayedRecord.triage.priority_tier,
        score_delta:
          (replayedRecord.triage.priority_score ?? 0) -
          (original.triage.priority_score ?? 0),
        reason_codes_added: reason_codes.filter(
          (c) => !original.triage.reason_codes.includes(c),
        ),
        reason_codes_removed: original.triage.reason_codes.filter(
          (c) => !reason_codes.includes(c),
        ),
      },
    });
  } catch (err) {
    next(err);
  }
});
