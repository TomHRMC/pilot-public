# ⚔️ Conflict Resolution: Data Sync Logic Rules

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. Conflict Detection Mandate

The Integrations Lead must implement automated conflict detection for all bi-directional sync operations. A conflict is defined as any instance where an entity (e.g., a Customer or Expense) has been modified in both Pilot for Trades and QuickBooks since the last successful sync timestamp.

## 2. Sync Direction & Master Rules

The agent must adhere to the following default "Master" designations unless a manual override is triggered:

| Entity Type | Master System | Logic Constraint |
| --- | --- | --- |
| **Customers** | **User Choice** | The system must pause the sync for that record and flag it for manual resolution. |
| **Quotes** | **Pilot for Trades** | Pilot for Trades is the source of truth for estimates; push updates to QuickBooks. |
| **Invoices** | **QuickBooks** | Final billing and tax data in QuickBooks supersede Pilot for Trades drafts. |
| **Payments** | **QuickBooks** | Pilot for Trades is read-only for payment status; never overwrite QuickBooks payment data. |
| **Expenses** | **User Choice** | Allow the user to select which receipt or categorization is correct. |

## 3. Resolution Flow Logic

When a conflict is detected, the Integrations Lead must manage the following state machine:

1. **Identify**: Mark the record status as `CONFLICT` in the `Sync Mappings` table.
2. **Notify**: Trigger a **P3 - Medium** alert to the user's dashboard.
3. **UI Presentation**: Present the user with a side-by-side comparison of the Pilot for Trades version vs. the QuickBooks version.
4. **User Choice**:
* **Keep Pilot for Trades**: Update QuickBooks with Pilot for Trades data and refresh the sync timestamp.
* **Keep QuickBooks**: Update the Pilot for Trades PostgreSQL record to match QuickBooks and refresh the timestamp.


5. **Finalize**: Mark the conflict as `RESOLVED` and log the decision in the `Sync History`.

## 4. Bulk Sync Constraints

* **Batch Limits**: For initial imports or bulk updates, limit batches to **1,000 records** to prevent API timeouts or rate-limiting (429) errors.
* **Conflict Deferral**: During a bulk sync, if more than 50 conflicts are detected, the sync should be paused to prevent a "dirty data" cascade.

## 5. Audit & Security

* **Sync History**: Every resolution must be logged in the `Sync History` table, including the `user_id` who made the decision and the `X-Request-ID` for the transaction.
* **Integrity Check**: Before applying any "Keep Pilot for Trades" resolution, verify that the target QuickBooks `SyncToken` matches to prevent overwriting third-party updates made during the resolution window.
