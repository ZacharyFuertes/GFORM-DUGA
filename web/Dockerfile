FROM mcr.microsoft.com/playwright:v1.64.0-noble

WORKDIR /app

# The Playwright base image ships a non-root user; build as root.
USER root

# Install only production deps, and make the workspace links resolve.
COPY package.json package-lock.json tsconfig.base.json ./
COPY packages/core/package.json packages/core/package.json
COPY apps/worker/package.json apps/worker/package.json

RUN npm ci --omit=dev --no-audit --no-fund

# Copy the two source packages (worker + shared core).
COPY packages/core packages/core
COPY apps/worker apps/worker

ENV NODE_ENV=production

# Node ships native TypeScript support (>=23.6), so no build step is needed.
CMD ["node", "apps/worker/src/main.ts"]