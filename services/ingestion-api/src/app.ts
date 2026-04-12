import express from 'express';
import { healthRouter } from './routes/health';
import { ingestRouter } from './routes/ingest';
import { incidentsRouter } from './routes/incidents';
import { replayRouter } from './routes/replay';
import { errorHandler } from './middleware/error-handler';

export function createApp() {
  const app = express();

  app.use(express.json({ limit: '1mb' }));

  // CORS for local dashboard development
  app.use((_req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    next();
  });

  app.use('/health', healthRouter);
  app.use('/ingest', ingestRouter);
  app.use('/incidents', incidentsRouter);
  app.use('/replay', replayRouter);

  app.use(errorHandler);

  return app;
}
