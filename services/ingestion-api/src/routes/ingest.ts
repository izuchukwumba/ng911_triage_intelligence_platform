import { Router } from 'express';
import { parseTranscript } from '@ng911/transcript-parser';
import { scoreIncident } from '@ng911/prioritization-engine';
import { IncidentRecordSchema } from '@ng911/incident-schema';
import { getStore } from '../store';

export const ingestRouter = Router();

/**
 * POST /ingest
 *
 * Accept a raw transcript, run the full parse+score pipeline,
 * persist the resulting incident record, and return it.
 *
 * Body: { "text": "someone has been shot near 5th street..." }
 */
ingestRouter.post('/', (req, res, next) => {
  try {
    const { text } = req.body as { text?: unknown };

    if (!text || typeof text !== 'string' || text.trim().length === 0) {
      res.status(400).json({ error: '`text` field is required and must be a non-empty string' });
      return;
    }

    // Parse transcript into a structured incident object
    const parsed = parseTranscript(text);

    // Score the parsed incident
    const { priority_score, priority_tier, reason_codes, scoring_version, score_breakdown } =
      scoreIncident(parsed);

    // Merge triage and audit fields back
    const record = {
      ...parsed,
      triage: { priority_score, priority_tier, reason_codes },
      audit: { ...parsed.audit, scoring_version },
    };

    getStore().save(record);

    res.status(201).json({ incident: record, score_breakdown });
  } catch (err) {
    next(err);
  }
});

/**
 * POST /ingest/score
 *
 * Re-score an existing (or externally-provided) incident record.
 * Useful for evaluating scoring config changes without re-parsing.
 *
 * Body: a full IncidentRecord object
 */
ingestRouter.post('/score', (req, res, next) => {
  try {
    const parseResult = IncidentRecordSchema.safeParse(req.body);

    if (!parseResult.success) {
      res.status(400).json({
        error: 'Invalid incident record',
        details: parseResult.error.flatten(),
      });
      return;
    }

    const result = scoreIncident(parseResult.data);
    res.json(result);
  } catch (err) {
    next(err);
  }
});
