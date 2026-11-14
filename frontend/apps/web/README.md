### 1\. The Web App README (`apps/web/README.md`)

Replace the default Next.js boilerplate in `apps/web/README.md` with this:

````markdown
# 🖥️ Pilot Web Dashboard

This is the Next.js web application for **Pilot For Trades AI**.

## 🎯 Purpose & Persona

This application is designed specifically for **business owners and bookkeepers**. It is a data-dense, keyboard-and-mouse-optimized dashboard. Its primary functions include:

- Complex reporting and financial AR aging dashboards.
- Deep, multi-level data tables (Quotes, Jobs, Invoices).
- QuickBooks integration management.
- Tenant and subscription administration.

## 🛠️ Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: `shadcn/ui`
- **Data Fetching**: `@pilot/shared-api` (Axios + TanStack Query)
- **Performance**: React Compiler enabled (no manual memoization needed).

## 🚀 Running Locally

Because this app is part of a Turborepo workspace, you should ideally run it from the root `frontend/` directory.

To start _only_ the web application:

```bash
# Run from the root pilot/frontend/ directory
pnpm run dev --filter web
```
````

Open [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000) in your browser to see the result.

## 🌐 Environment Variables

The web app requires a `.env.local` file in the `apps/web/` directory:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## 🧩 Adding UI Components

We use `shadcn/ui` for our component library. Components are not installed as NPM packages; instead, their source code is copied directly into our repository so we maintain 100% ownership.

To add a new component (e.g., a button), navigate to `apps/web/` and run:

```bash
npx shadcn@latest add button
```
