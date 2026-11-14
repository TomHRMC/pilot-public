# 📖 API Type Synchronization (`openapi-typescript`)

This folder utilizes the `openapi-typescript` tool to automatically generate perfectly typed TypeScript interfaces from our backend's FastAPI OpenAPI schema.

## Why do we need this?

Instead of manually typing out TypeScript interfaces that might fall out of sync with the backend, this tool reads the backend's exact data contracts (Pydantic models) and generates a single source of truth. This gives us perfect autocomplete, prevents UI bugs, and immediately highlights errors if the backend changes a payload structure.

## Expected Output

Running the synchronization command reads `../backend/openapi.json` and outputs a comprehensive TypeScript declaration file at: `packages/shared-types/src/api-schema.d.ts`

## How to Run It

We have automated the two-step process (exporting from Python, then generating in TypeScript) into a single npm script.

From the `frontend/` directory, run:

```bash
pnpm run sync-api-types
```

## Generating Directly from a Running API Server

Instead of the standard process above (which reads the committed `openapi.json` file), you can also generate the TypeScript interfaces directly from the API web server:

```bash
pnpm --filter @pilot/shared-types run generate
```
