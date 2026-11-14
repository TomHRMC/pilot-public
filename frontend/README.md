# Pilot for Trades: Frontend Monorepo

Welcome to the frontend workspace for **Pilot for Trades**, the AI-powered quoting and profitability tracker for electrical contractors.

This repository is a **Turborepo** monorepo containing the Web Dashboard (Next.js), the Mobile Field App (Expo), and the Marketing Static Site (Next.js static export), sharing a unified type system and API client directly linked to our FastAPI backend.

---

## 🏗️ Architecture: What's Inside?

This monorepo uses `pnpm` workspaces to manage multiple applications and shared libraries in a single repository.

### Applications (`apps/`)

- **`apps/web`**: A [Next.js](https://nextjs.org/) (App Router) web application. Optimized for data-dense, mouse-and-keyboard interactions for business owners and bookkeepers. Styled with Tailwind CSS and `shadcn/ui`. Runs on **port 3000**.
- **`apps/mobile`**: An [Expo](https://expo.dev/) (React Native) mobile application. Optimized for offline-capable, high-contrast field use by electrical technicians. Styled with `gluestack-ui`.
- **`apps/marketing`**: A [Next.js](https://nextjs.org/) (App Router) **static export** marketing site (`output: "export"`). Designed for public-facing landing pages, SEO, and lead capture. Runs on **port 3001**. Produces a fully static `out/` directory that can be deployed to any CDN (S3/CloudFront, Vercel, Netlify).

### Shared Packages (`packages/`)

- **`@pilot/shared-types`**: 100% auto-generated TypeScript interfaces derived directly from the FastAPI `openapi.json` schema. Ensures database-to-UI type safety.
- **`@pilot/shared-api`**: The universal Axios client and TanStack Query data-fetching hooks. Used by both the Web and Mobile apps.
- **`@pilot/ui`**: Shared UI components (including the voice-stream and confirm-turn components).
- **`@repo/eslint-config`**: Shared `eslint` configurations to keep code style identical across platforms.
- **`@repo/typescript-config`**: Shared `tsconfig.json` configurations.

---

## 🚀 Getting Started

### 1. Prerequisites

Ensure you have the following installed on your machine:

- **Node.js** (v20+; Next.js 16 requires it)
- **pnpm** (`npm install -g pnpm`)
- The **FastAPI Backend** (Make sure your Python server is running on `http://127.0.0.1:8000`)

### 2. Environment Variables

You need to point your frontend apps to the FastAPI backend.

**For Web (`apps/web/.env.local`):**

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

**For Mobile (`apps/mobile/.env`):**

```env
# Note: For physical device testing, replace 127.0.0.1 with your computer's local Wi-Fi IP.
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 3. Installation

Navigate to the root of the `frontend/` directory and install all dependencies (this will automatically link the workspace packages):

```bash
pnpm install
```

### 4. Running the Development Servers

To spin up all three apps simultaneously, run:

```bash
pnpm run dev
```

**What you will see:**

- **Web App** → `http://localhost:3000`: The Pilot for Trades dashboard app. Sign in with the dev account (or mock mode) to reach the dashboard.
- **Marketing Site** → `http://localhost:3001`: The static marketing landing page. No backend connection required — fully standalone.
- **Mobile App**: Your terminal will display an Expo QR code. Press `i` to open the iOS simulator, `a` for Android, or scan the QR code with the Expo Go app on your phone. Sign in with the dev account (or mock mode) to reach the home screen.

> **Port Note**: `apps/web` uses Next.js's default port 3000. `apps/marketing` is pinned to port 3001 via `"dev": "next dev -p 3001"` to avoid conflicts.

---

## 🧠 How the Shared Packages Work

### Generating TypeScript Interfaces

Instead of manually typing database models, we generate them directly from FastAPI.

If you make a change to a SQLAlchemy model or Pydantic schema in the backend, follow these steps to update the frontend:

1. Ensure your FastAPI server is running.
2. In the `frontend/` directory, run:
   ```bash
   pnpm --filter @pilot/shared-types run generate
   ```
   This updates `packages/shared-types/src/schema.d.ts` (the main pipeline is `pnpm sync-api-types`, which writes `api-schema.d.ts`) with your backend schema, instantly updating autocomplete and type-checking across your entire web and mobile codebase.

### Shared API & React Compiler

- **API Fetching**: If you need to write a new API call, put it in `packages/shared-api/src/`. Export it, and simply import it into Next.js or Expo as `import { myNewCall } from "@pilot/shared-api"`.
- **React Compiler**: Both apps have the **React Compiler** enabled. You do not need to manually write `useMemo` or `useCallback`. The build pipeline will automatically memoize your components for peak performance.

---

## 🛡️ Git Hooks & Code Quality

This monorepo is protected by **Husky** and **lint-staged**.
When you run `git commit`, Husky intercepts the commit and automatically runs Prettier and ESLint on your changed files. If there are syntax errors, the commit will be blocked until you fix them.

To format your code manually, run:

```bash
pnpm run format
```

---

## ⚙️ Turborepo Commands & Utilities

This monorepo utilizes [Turborepo](https://turborepo.org/) to orchestrate tasks efficiently via caching.

### Build

To build all apps and packages:

```bash
# Build everything
pnpm run build

# Build only the web dashboard
pnpm --filter web run build

# Build only the marketing static site (outputs to apps/marketing/out/)
pnpm --filter marketing run build
```

> **Marketing static output**: After `pnpm --filter marketing run build`, the fully static site is available at `apps/marketing/out/`. Deploy this directory directly to S3/CloudFront, Vercel, or Netlify.

### Remote Caching (Optional)

Turborepo can use [Remote Caching](https://turborepo.dev/docs/core-concepts/remote-caching) to share cache artifacts across your team and CI/CD pipelines.

```bash
npx turbo login
npx turbo link
```

### Useful Links

- [Turborepo Tasks](https://turborepo.dev/docs/crafting-your-repository/running-tasks)
- [Turborepo Filtering](https://turborepo.dev/docs/crafting-your-repository/running-tasks#using-filters)
- [Next.js Documentation](https://nextjs.org/docs)
- [Expo Documentation](https://docs.expo.dev/)
