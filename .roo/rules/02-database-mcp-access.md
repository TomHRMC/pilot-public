# Database MCP Access — All Agent Modes

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

Two PostgreSQL MCP servers are available in the Roo Code extension. **Both connections are read-only.** They are for schema/data **verification only** — never a substitute for a migration, seed script, or application code, and never used to INSERT/UPDATE/DELETE.

| MCP server | Target | When to use | Access gate |
|---|---|---|---|
| **`postgres-local`** | Local dev database | Default. All routine schema + data verification. | Always available — no gate. |
| **`postgres-prod`** | Production database (via SSH tunnel) | Only when the task explicitly requires verifying **production** state. | **Requires an SSH tunnel that only Tom controls.** Before your first `postgres-prod` query in a session, **ask Tom to confirm the SSH tunnel is up.** If a `postgres-prod` query errors with a connection failure, the tunnel is almost certainly down → STOP and ask Tom to bring it up; do not retry blindly or fall back to guessing. |

## Rules for both servers

1. **Read-only, always.** These MCPs verify table names, column types, constraints, indexes, triggers, and existing rows. Never use them to mutate data. All data changes go through Alembic migrations, seed scripts, or application code.
2. **`postgres-local` is the default authoritative source** for schema discovery during design and implementation. Prefer it unless the task is specifically about production drift, a prod incident, or confirming a prod-only data condition.
3. **`postgres-prod` needs the tunnel + Tom's confirmation.** Do not assume the tunnel is up. Ask first (using the `ask_followup_question` tool per `01-followup-suggestions.md`). Treat prod reads as sensitive (the environment held only the author's test data) — query only the columns you need; query only the columns you need.
4. **Filter by schema.** Every query must filter `table_schema IN ('public', 'audit')` to avoid empty results or thousands of system objects.
5. **No SQLite syntax.** This is strictly PostgreSQL — never `PRAGMA` or `SHOW TABLES`.
6. **On any error → STOP and ask Tom.** A failed query (especially on `postgres-prod`) is a signal, not something to work around.

## Query patterns

Use the canonical, verified query snippets in
[`dev-docs/db-design/postgres-mcp-guide.md`](../../dev-docs/db-design/postgres-mcp-guide.md)
for columns, PKs, FKs, indexes, triggers, functions, and CHECK/EXCLUDE constraints.
