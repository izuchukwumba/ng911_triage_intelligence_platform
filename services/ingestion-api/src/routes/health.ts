import { Router } from 'express';
import { getStore } from '../store';

export const healthRouter = Router();

healthRouter.get('/', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'ng911-ingestion-api',
    incident_count: getStore().count(),
    timestamp: new Date().toISOString(),
  });
});
