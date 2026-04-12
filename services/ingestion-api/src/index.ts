import { createApp } from './app';

const PORT = parseInt(process.env['PORT'] ?? '3001', 10);

const app = createApp();

app.listen(PORT, () => {
  console.log(`[ng911-ingestion-api] Listening on http://localhost:${PORT}`);
  console.log(`  POST /ingest          — submit a transcript`);
  console.log(`  POST /ingest/score    — re-score an incident record`);
  console.log(`  GET  /incidents       — list all incidents`);
  console.log(`  GET  /incidents/:id   — get incident by ID`);
  console.log(`  POST /replay/:id      — replay parse+score for an incident`);
  console.log(`  GET  /health          — service health`);
});
