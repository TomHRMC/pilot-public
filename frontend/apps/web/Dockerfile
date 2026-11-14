# =============================================================================
# Pilot Web — Production Dockerfile
# =============================================================================
#
# Build context MUST be the monorepo root (frontend/), not apps/web/, because
# the web app has workspace deps in packages/shared-api, packages/ui, etc.
#
# Build command (run from the repo root):
#   docker build --platform linux/amd64 \
#     -f frontend/apps/web/Dockerfile \
#     -t pilot-web:latest \
#     frontend/
#
# Tag and push:
#   docker tag pilot-web:latest 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
#   docker push 000000000000.dkr.ecr.us-east-1.amazonaws.com/pilot/web:latest
#
# IMPORTANT: NEXT_PUBLIC_* env vars are baked into the JS bundle at Next.js build
# time. They MUST be passed as --build-arg flags. Runtime injection does not work.
# See Step 4 below for the required ARG/ENV declarations and example build command.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: builder
# -----------------------------------------------------------------------------
FROM --platform=linux/amd64 node:20-alpine AS builder

RUN apk add --no-cache libc6-compat

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# ── Step 1: Copy manifests + lockfile (cache layer) ──────────────────────────
# These rarely change → pnpm install layer is cached across most builds.
COPY pnpm-workspace.yaml ./
COPY .npmrc              ./
COPY package.json        ./
COPY pnpm-lock.yaml      ./
COPY turbo.json          ./

# Copy every workspace package.json (needed for pnpm workspace protocol linking)
COPY apps/web/package.json                  ./apps/web/package.json
COPY packages/shared-api/package.json       ./packages/shared-api/package.json
COPY packages/shared-types/package.json     ./packages/shared-types/package.json
COPY packages/ui/package.json               ./packages/ui/package.json
COPY packages/eslint-config/package.json    ./packages/eslint-config/package.json
COPY packages/typescript-config/package.json ./packages/typescript-config/package.json

# ── Step 2: Install ───────────────────────────────────────────────────────────
# pnpm creates node_modules with its virtual-store symlinks here.
# We must NOT use COPY . . after this point — doing so would attempt to write
# real directories over those symlinks, causing BuildKit to error:
#   "cannot copy to non-directory: …/node_modules/@eslint/config-array"
RUN pnpm install --frozen-lockfile

# ── Step 3: Copy source — explicit paths only, node_modules never touched ────
# Root-level config files
COPY .npmrc      ./

# apps/web — source and config files only (no node_modules, no .next)
COPY apps/web/src/               ./apps/web/src/
COPY apps/web/src/types/         ./apps/web/src/types/
COPY apps/web/public/            ./apps/web/public/
COPY apps/web/next.config.ts     ./apps/web/next.config.ts
COPY apps/web/tsconfig.json      ./apps/web/tsconfig.json
COPY apps/web/tailwind.config.ts ./apps/web/tailwind.config.ts
COPY apps/web/postcss.config.mjs ./apps/web/postcss.config.mjs
COPY apps/web/next-env.d.ts      ./apps/web/next-env.d.ts

# packages/shared-api
COPY packages/shared-api/src/ ./packages/shared-api/src/

# packages/shared-types
COPY packages/shared-types/src/ ./packages/shared-types/src/

# packages/ui
COPY packages/ui/src/              ./packages/ui/src/
COPY packages/ui/tsconfig.json     ./packages/ui/tsconfig.json
COPY packages/ui/tailwind.preset.ts ./packages/ui/tailwind.preset.ts

# packages/eslint-config (JS config files, no src/ directory)
COPY packages/eslint-config/base.js            ./packages/eslint-config/base.js
COPY packages/eslint-config/next.js            ./packages/eslint-config/next.js
COPY packages/eslint-config/pilot.js           ./packages/eslint-config/pilot.js
COPY packages/eslint-config/react-internal.js  ./packages/eslint-config/react-internal.js
COPY packages/eslint-config/rules/             ./packages/eslint-config/rules/

# packages/typescript-config (JSON config files only)
COPY packages/typescript-config/base.json          ./packages/typescript-config/base.json
COPY packages/typescript-config/nextjs.json        ./packages/typescript-config/nextjs.json
COPY packages/typescript-config/react-library.json ./packages/typescript-config/react-library.json

# ── Step 4: Build ─────────────────────────────────────────────────────────────
# NEXT_PUBLIC_* vars are baked into the JS bundle at build time by Next.js.
# They CANNOT be injected at runtime — they must be passed as Docker build args.
#
# Required build args (pass via --build-arg):
#   NEXT_PUBLIC_COGNITO_USER_POOL_ID   e.g. us-east-1_XXXXXXXXX
#   NEXT_PUBLIC_COGNITO_APP_CLIENT_ID  e.g. xxxxxxxxxxxxxxxxxxxxxxxxxx
#   NEXT_PUBLIC_COGNITO_REGION         e.g. us-east-1
#   NEXT_PUBLIC_API_URL                e.g. https://api.pilotfortrades.com
#   NEXT_PUBLIC_TENANT_SITES_DOMAIN    e.g. p4tsites.com (C-B16-OPS, ADR-0014)
#
# Build command example (from §8.3 of the ops runbook):
#   docker build --platform linux/amd64 \
#     --build-arg NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX \
#     --build-arg NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx \
#     --build-arg NEXT_PUBLIC_COGNITO_REGION=us-east-1 \
#     --build-arg NEXT_PUBLIC_API_URL=https://api.pilotfortrades.com \
#     --build-arg NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com \
#     -f frontend/apps/web/Dockerfile \
#     -t pilot-web:latest \
#     frontend/
ARG NEXT_PUBLIC_COGNITO_USER_POOL_ID
ARG NEXT_PUBLIC_COGNITO_APP_CLIENT_ID
ARG NEXT_PUBLIC_COGNITO_REGION=us-east-1
ARG NEXT_PUBLIC_API_URL=https://api.pilotfortrades.com
ARG NEXT_PUBLIC_TENANT_SITES_DOMAIN=p4tsites.com
# TS-BUG-1: non-public var — read at RUNTIME by proxy.ts (Node.js runtime),
# NOT inlined at build time like NEXT_PUBLIC_*. The ECS task definition env
# var overrides this default without requiring a rebuild.
# NOTE: proxy.ts also has a multi-domain fallback that tries p4tsites.com and
# localhost even if env vars are stale — so this is belt-and-suspenders.
ARG TENANT_SITES_DOMAIN=p4tsites.com

ENV NEXT_PUBLIC_COGNITO_USER_POOL_ID=$NEXT_PUBLIC_COGNITO_USER_POOL_ID
ENV NEXT_PUBLIC_COGNITO_APP_CLIENT_ID=$NEXT_PUBLIC_COGNITO_APP_CLIENT_ID
ENV NEXT_PUBLIC_COGNITO_REGION=$NEXT_PUBLIC_COGNITO_REGION
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_TENANT_SITES_DOMAIN=$NEXT_PUBLIC_TENANT_SITES_DOMAIN
ENV TENANT_SITES_DOMAIN=$TENANT_SITES_DOMAIN

WORKDIR /app/apps/web
RUN pnpm build

# -----------------------------------------------------------------------------
# Stage 2: runner — minimal production image (~100 MB, no build tooling)
# -----------------------------------------------------------------------------
FROM --platform=linux/amd64 node:20-alpine AS runner

# curl is required for the ECS container health check:
#   CMD-SHELL: curl -f http://localhost:3000/api/health || exit 1
# Without curl, every health check fails with "exec: curl not found" → container
# is marked UNHEALTHY and killed after startPeriod + (retries × interval).
RUN apk add --no-cache libc6-compat curl

# Security: non-root user
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# The standalone bundle is copied to /app (monorepo root), so server.js lives at
# /app/apps/web/server.js. Next.js standalone server.js resolves .next/ and pages
# relative to __dirname (its own directory). WORKDIR must be /app/apps/web so that:
#   - server.js finds .next/ at ../../../apps/web/.next (relative paths inside server.js)
#   - The health check path /api/health resolves correctly
#   - ALB target-group health check GET /api/health → HTTP 200 succeeds
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
# TS-BUG-1: non-public runtime env var for proxy.ts host-rewrite.
# The ECS task definition sets TENANT_SITES_DOMAIN=p4tsites.com — this default
# ensures it's present even if the task def doesn't override it.
# NOTE: proxy.ts reads the Host header directly + tries multiple candidate
# domains, so this env var is belt-and-suspenders, not a hard dependency.
ENV TENANT_SITES_DOMAIN=p4tsites.com

# The standalone bundle is fully self-contained — no other node_modules needed.
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static     ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public           ./apps/web/public

USER nextjs

EXPOSE 3000

# CRITICAL: WORKDIR must match the directory containing server.js.
# server.js uses __dirname to resolve .next/ and public/ assets.
# Running from /app (with CMD ["node", "apps/web/server.js"]) causes 404 on all routes
# because __dirname becomes /app/apps/web but the CWD is /app, breaking relative lookups.
# Running from /app/apps/web (with CMD ["node", "server.js"]) is the canonical pattern.
WORKDIR /app/apps/web
CMD ["node", "server.js"]
