import { Router } from 'express';
import { getStore } from '../store';

export const incidentsRouter = Router();

/**
 * GET /incidents
 *
 * List all incidents, sorted by received_at descending.
 * Supports ?limit, ?offset, ?domain, ?priority_tier query params.
 */
incidentsRouter.get('/', (req, res) => {
  const limit = parseInt(req.query['limit'] as string ?? '50', 10);
  const offset = parseInt(req.query['offset'] as string ?? '0', 10);
  const domain = req.query['domain'] as string | undefined;
  const priority_tier = req.query['priority_tier'] as string | undefined;

  const page = getStore().findAll({
    limit: isNaN(limit) ? 50 : limit,
    offset: isNaN(offset) ? 0 : offset,
    domain,
    priority_tier,
  });

  res.json(page);
});

/**
 * GET /incidents/:id
 *
 * Retrieve a single incident by its UUID.
 */
incidentsRouter.get('/:id', (req, res) => {
  const incident = getStore().findById(req.params['id'] ?? '');

  if (!incident) {
    res.status(404).json({ error: `Incident ${req.params['id']} not found` });
    return;
  }

  res.json(incident);
});
