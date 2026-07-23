# syntax=docker/dockerfile:1
# Front-end (Next.js) image (Phase 11). Multi-stage: install + build, then a slim
# runner serving the standalone output. The browser reaches the API through the
# Next rewrite (MMM_OS_API_URL); the front-end never touches the backend DB.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
COPY prisma ./prisma
# Prisma's postinstall needs the schema; deterministic install from the lockfile.
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run prisma:generate && npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
RUN useradd --create-home --uid 10001 nextjs
USER nextjs

# The standalone server bundles only what it needs; copy static + public alongside.
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
