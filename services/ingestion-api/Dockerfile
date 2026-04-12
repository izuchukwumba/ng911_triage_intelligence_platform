FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace manifests for dependency install
COPY package.json package-lock.json ./
COPY packages/incident-schema/package.json     packages/incident-schema/
COPY packages/location-validator/package.json  packages/location-validator/
COPY services/transcript-parser/package.json   services/transcript-parser/
COPY services/prioritization-engine/package.json services/prioritization-engine/
COPY services/ingestion-api/package.json       services/ingestion-api/

RUN npm install --workspaces --include-workspace-root

# Copy source
COPY tsconfig.base.json ./
COPY packages/ packages/
COPY services/ services/

# Build all workspace packages
RUN npm run build --workspaces --if-present

# ---- runtime image ----
FROM node:20-alpine AS runtime

WORKDIR /app

COPY --from=builder /app/node_modules        ./node_modules
COPY --from=builder /app/packages            ./packages
COPY --from=builder /app/services/ingestion-api/dist ./services/ingestion-api/dist
COPY --from=builder /app/services/ingestion-api/package.json ./services/ingestion-api/

ENV NODE_ENV=production
EXPOSE 3001

CMD ["node", "services/ingestion-api/dist/index.js"]
