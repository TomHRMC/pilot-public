# UI Testing Issues — Round 2 (July 10, 2026 — Evening Session)

---

## 🔴 Reports Page — Drill-Down Panel: Job Number Missing, Customer Name Missing

**Component**: `DrillDownPanel.tsx`

**Current columns**: Job (title/label), Closed (date), Revenue, Margin
**What "Job" shows**: `job.title` which maps to `r.group_label` from the backend profitability aggregation endpoint — currently showing either a UUID or an aggregated label, not a human-readable job number

**Required changes:**

| Column | Current | Required |
|---|---|---|
| "Job #" | `group_label` (UUID or label) | `job_number` (e.g. JOB-20260701-ABC) — requires B18 to add `job_number` to job table |
| "Job Title" | `group_label` (same garbled value) | `quote.title` / project name (e.g. "Main Panel Upgrade") — requires B18 to add `title` to `quote` table; propagated to job detail |
| "Customer" | ❌ Not a column | Add `customer_name` column — from customer JOIN in profitability endpoint |

**Root cause analysis:**

1. **`ClosedJob` interface** in `useProfitability.ts` line 69 only has `id`, `title`, `close_date`, `revenue_cents`, `margin_pct`, `margin_bucket` — no `customer_name` or `job_number`

2. **Data adapter** (line 160) maps `r.group_key` → `id` and `r.group_label` → `title` — both come from the backend profitability aggregation endpoint's raw response shape

3. **Backend profitability endpoint** — `GET /api/v1/reports/profitability` returns aggregated rows. The `group_label` and `group_key` fields need to include `job_number` and `customer_name` in the raw response, OR the frontend must fetch additional job detail per row

**Recommended fix (backend first, then frontend):**

**B18 backend scope addition**: After adding `job_number` to the `job` table, also update the profitability report endpoint's aggregated row response to include `job_number` and `customer_name` fields in `RawProfitabilityReportRow`. The profitability query already JOINs the `job` table — adding these two fields is a straightforward SELECT addition.

**FE-B25 frontend scope addition**:
1. Add `job_number: string` and `customer_name: string` to `ClosedJob` interface
2. Update data adapter to map `r.job_number` and `r.customer_name` from raw backend response
3. Update `DrillDownPanel.tsx` to:
   - Rename "Job" column header to "Job #"
   - Render `job.job_number` in the first column (not `job.title`)
   - Add "Customer" column after "Job #", rendering `job.customer_name`

**Priority**: 🔴 Critical for demo — without readable job IDs and customer names, the profitability drill-down is not usable for a real owner.

**Depends on**: B18 (adds `job_number` to DB + profitability endpoint)

---

---

## 🟡 Comms Page — "To/From" Context Missing on Messages (Multi-Tech Readability Gap)

### Current Behavior (1 Tech)

**On the Customer Comms tab** (`/customers/{id}/comms`):

Each thread group collapsible header shows:
- Tech name (e.g. "Dev Technician")
- Date range of the thread
- Message count
- Originating job label (if linked)

Each message bubble shows:
- Direction-based alignment: outbound messages (from tech → customer) are right-aligned blue; inbound messages (from customer → tech) are left-aligned gray
- Message body text
- Timestamp

**What is NOT shown**:
- ❌ The customer's name is not shown on any message bubble (it's implied by context since you're on the customer's page)
- ❌ No explicit "To: [customer name]" or "From: [tech name]" label on each bubble
- ❌ The message direction arrows/labels are the only indicator of who sent what

**On the global Comms page** (`/comms`):
- Shows threads across ALL customers for the tenant
- Thread headers show tech name but NOT customer name prominently

### What You'll See With 5 Technicians

**Customer Comms tab**: Multiple thread groups, each with a different tech name in the header. The bubbles don't label who sent each message — you have to correlate the tech name from the thread group header to the bubbles inside. If a thread has both inbound (customer) and outbound (tech) messages alternating, the alignment is the only indicator.

**Global Comms page**: The thread list will show tech names, but to understand which customer each conversation is with, the user must read the thread URL or click in — the customer name may not be prominently shown on the thread list card.

### Gaps to Fix

| Gap | Location | Severity |
|---|---|---|
| Global comms page doesn't prominently show customer name on thread cards | Global `/comms` page thread list | � Critical with multi-tech |
| Message bubbles have no "From: [name]" label on either side | `SmsThreadBubble.tsx` | 🟡 Important — direction-color is sufficient for 1:1, but ambiguous with multiple techs |
| Customer name not visible on customer comms tab thread bubbles | `CommThreadGroup.tsx` / `CustomerCommsHistoryView` | 🟢 Low — implied by page context |

**Required fix 1 — Global Comms page thread cards** (🔴 MVP Required):
- Customer name must be the **primary identifier** on each thread list card, not the tech name
- Thread card should show: **[Customer Name]** (large/bold) · [Tech Name] (secondary) · [Date] · [Unread count]
- Currently customer name is either absent or de-emphasized — critical gap with multi-customer accounts

**Required fix 2 — Message bubble sender labels** (🔴 MVP Required — Tom confirmed):
- Every message bubble must show a small "From: [Name]" label so the user always knows who sent each message
- **Outbound** (tech → customer): show "From: [Tech First Name]" below or beside the bubble
- **Inbound** (customer → tech): show "From: [Customer First Name]" below or beside the bubble
- This makes the conversation readable without relying on bubble color + direction alone

**Implementation note for message bubbles**:
`SmsThreadBubble` currently does NOT receive sender names — it only knows `direction` and `body`. The sender name must be passed as a prop from the parent `CommThreadGroup`, which already has `thread.tech_name`. The customer name comes from the parent context (the customer page or thread data). The `SmsThreadBubble` component needs a new optional prop:
```typescript
// Add to SmsThreadBubbleProps:
senderLabel?: string; // e.g. "From: Jake" or "From: John Smith"
```
The `CommThreadGroup` passes:
- For outbound messages: `senderLabel={thread.tech_name.split(' ')[0]}` (first name)
- For inbound messages: `senderLabel={thread.customer_name}` (if available in thread data) or passed from parent

**Priority**: 🔴 Required for MVP — add to **FE-B24**.

---

---

## 🔴 Comms Page Text Too Small — Design System Token Mismatch

**Root cause identified**: The comms page components use semantic design tokens from `tailwind.preset.ts`. The other list pages (Jobs, Customers, Quotes, Invoices) use Tailwind's direct size classes. The two systems use different pixel sizes:

| Token / Class | Pixel Size | Used In |
|---|---|---|
| `text-caption` | **11px** | Comms — thread dates, message counts, timestamps |
| `text-body` | **13px** | Comms — tech name header, message bubble text |
| `text-sm` (Tailwind) | **14px** | Jobs, Customers, Quotes, Invoices — all table rows |
| `text-xs` (Tailwind) | **12px** | Various secondary labels |

**Effect**: The comms thread list headers (`text-body` = 13px) render 1px smaller than jobs/customers table rows (`text-sm` = 14px). The comms timestamps and metadata (`text-caption` = 11px) render 3px smaller.

**Fix options:**

| Option | Scope | Risk |
|---|---|---|
| **A** (recommended): Increase `text-body` token from 13px → 14px in `tailwind.preset.ts` | System-wide — affects ALL `text-body` usage across the entire app | Medium — need to audit all `text-body` occurrences; any component that was sized for 13px may shift layout |
| **B**: Change comms-specific components to use `text-sm` instead of `text-body` | Only comms components affected | Low — targeted change, no system-wide impact; inconsistency remains between design token system and direct classes |
| **C**: Change all other list pages to use `text-body` instead of `text-sm` | All list page tables affected | Low risk to comms; medium risk if tables were designed for 14px |

**Architect recommendation**: Option A (increase `text-body` to 14px) is the correct long-term fix because `text-sm` IS the standard body size in Tailwind and the design system should match. However, before doing this, run a visual audit of all components using `text-body` to ensure nothing breaks.

**Short-term workaround**: Option B — change `CommThreadGroup.tsx` to use `text-sm` instead of `text-body` for the thread header (tech name line) and `text-xs` instead of `text-caption` for secondary metadata. This makes comms match other pages without touching the global preset.

**Affected comms files:**
- `CommThreadGroup.tsx` — `text-body` on tech name (line 62), `text-caption` on date range (line 65) and job display (line 72)
- `SmsThreadBubble.tsx` — `text-body` on message text (line 58), `text-caption` on timestamp (line 70)

**Priority**: 🔴 Critical — unreadable text affects demo. Add Option B (targeted fix) to **FE-B24**. Option A (global preset fix) should be a separate decision with Tom + architect.

---

---

## ✅ Decision Made: Auto-Save Pattern — Surface-Specific Rules

**Status**: Decision reached by Tom + Architect (2026-07-11). Ready for engineering.

**Decided**: Auto-save on blur is only acceptable for **freeform notes / text areas** where the mental model is a "notepad". All structured form fields use explicit Save buttons.

### Auto-Save Rules by Surface

| Surface | Pattern | Notes |
|---|---|---|
| `JobNotesTab.tsx` | ✅ **Auto-save on blur** | Freeform notes — low-stakes, interruption-prone field context |
| `Settings/MyAccount/Profile` | ❌ **Explicit Save button** | High-stakes profile/account data — users must confirm intent |
| `JobPropertiesPanel.tsx` | ❌ **Explicit Save button** | Job properties are structured fields — owner must be 100% sure all changes are saved before leaving |
| `CustomerOverviewTab.tsx` | ❌ **Explicit Save button** | CRM data — accidental saves on structured customer fields are disruptive |

### UX Requirements for Auto-Save Surfaces (Job Notes)

The current "Saving…" / "Saved" / "Error" status text is too subtle. The auto-save confirmation UX **must** make it obvious to the user that:
1. Their changes are being saved the moment they leave the field
2. The save succeeded (or failed)

**Required UX for `JobNotesTab.tsx`**:
- Prominent **"Saved ✓"** indicator — green checkmark + text, **not** a small corner toast
- Indicator placement: directly below the notes textarea (inline, adjacent to the field)
- Animation: briefly highlight the textarea border green on save success, then fade
- Size: indicator text must be at least `text-sm` (14px) — not `text-caption` (11px)
- Error state: if save fails, show red "Save failed — retrying…" inline with retry logic

### Engineering Tasks

| Task | Surface | Batch |
|---|---|---|
| `JobNotesTab.tsx` — Keep auto-save, upgrade inline "Saved ✓" indicator UX per spec above | Job Notes | **FE-B25** |
| `Settings/MyAccount/Profile` — Replace auto-save with explicit Save + Cancel buttons | Profile Settings | **FE-B25** |
| `JobPropertiesPanel.tsx` — Replace PATCH-on-blur with explicit Save button; show dirty state indicator when unsaved changes exist | Dispatch Board Properties Panel | **FE-B25** |
| `CustomerOverviewTab.tsx` — Verify if auto-saving; convert inline edit toggle to explicit Save/Cancel if so | Customer Overview | **FE-B25** |

---

---

## ✅ Decision Made: All Data Tables → `@tanstack/react-table`

**Tom has approved**: Every data table in the web app will be migrated to `@tanstack/react-table` (TanStack Table v8). This is the architecture decision for all list/grid surfaces.

**What TanStack Table provides** (replaces all individual implementations):
- Column resizing (drag headers to adjust width)
- Sortable columns (replaces manual sort state in each component)
- Text wrap per column (controlled by column `size` and cell CSS — replaces `truncate`/`whitespace-normal` decisions)
- Virtual scrolling for large datasets (future)
- Pinnable columns (future)
- Row selection (future)

**Scope of migration**: All list tables:
- Jobs page
- Customers page
- Quotes page
- Invoices page
- Catalog → Pricebook tab
- Catalog → Labor Rates tab
- Catalog → Markups tab
- Catalog → Supplier Items tab
- Comms thread list

**Comms message text wrap**: No longer a separate manual fix. The React Table migration will handle text wrap via column definition configuration — `whitespace-normal` applied at the column cell level during the migration.

**Table migration batch**: This is a substantial amount of work across many pages. Should be a dedicated batch (FE-B26 or FE-B27) after B18, FE-B24, and FE-B25 are complete. The sortable headers work planned for FE-B24 should be **deferred** to this dedicated React Table migration batch — do not implement manual sort state now only to throw it away in the React Table migration.

> **⚠️ FE-B24 scope update**: Remove "sortable column headers" tasks from FE-B24. They will be implemented correctly as part of the React Table migration batch. Adding manual sort state now creates throwaway work.

---

## ✅ Decision Made: Dispatch Board Day View is NOT React Table

**Tom has clarified**: The Dispatch Board Day view (schedule lane layout) is a **calendar-style surface**, not a data table. It should NOT use React Table.

**Layout requirements for the Dispatch Board Day view**:
- Lane columns have a **fixed minimum width** — they do not shrink below a minimum size even when the browser window is narrow
- When the browser window is too narrow to show all lanes, the view scrolls horizontally (overflow-x: scroll) rather than compressing columns
- Time axis (rows) is fixed-height per time slot
- Drag-and-drop job placement must work at fixed grid coordinates

**Implementation**: CSS `min-width` per lane column + `overflow-x: auto` on the board container. This is already a concern for the multi-day/week/month view redesign (Tom action item) — include this constraint in the design session.

**Applies to**: Dispatch Board Day view only. All other list/table surfaces use TanStack React Table as decided above.

---

---

## 🟡 All Tables — Resizable Columns (Excel-Style)

**Request**: All data tables should allow the user to drag column header borders to resize column width — the same interaction as Excel or Google Sheets column resize.

**Scope**: Applies to all tables: Jobs, Customers, Quotes, Invoices, all Catalog tabs, Comms thread list.

**Implementation**: This is a non-trivial shared component — not a simple CSS change. Options:

| Approach | Effort | Notes |
|---|---|---|
| Custom `ResizableTable` wrapper component | Medium | Build once in `packages/ui/`, wrap all existing tables. Requires `mousedown`/`mousemove`/`mouseup` drag logic with `col` width state per table instance. |
| `@tanstack/react-table` column resizing | Low-Medium | If tables were migrated to TanStack Table (the data grid layer), resizing is a built-in plugin. This is the recommended long-term approach. |
| `react-resizable-columns` or similar npm package | Low (install) | Check license, bundle size, and Tailwind CSS compatibility before adopting. Must check `package.json` first. |

**Architect recommendation**: This is a good opportunity to evaluate migrating all data tables to `@tanstack/react-table`. It provides column resizing, sortable headers (which we already need), virtual scrolling for large datasets, and pinnable columns — all in one solution. The migration is table-by-table and non-breaking.

**Do not implement per-table custom drag logic** — it creates maintenance debt when we have 8+ tables. Build or adopt one shared solution.

**Priority**: 🟡 Important — requires architect design decision on approach before engineering. Add to **Tom + Architect discussion** before FE-B24 starts. If `@tanstack/react-table` is approved, it changes how sortable headers are also implemented.

---

## 🟡 Comms Page — Message Column Text Wrap (and Global Text Wrap Policy)

### Immediate Fix: Comms Message Column

The message body column on the comms thread list currently uses `truncate` (CSS `text-overflow: ellipsis`, single line). Change to `whitespace-normal` (text wraps to multiple lines) so owners can read full message previews without clicking into each thread.

**File**: Find the comms thread list component — likely `frontend/apps/web/src/features/comms/` or similar. Change `truncate` class on the message body `<td>` to `whitespace-normal` (or remove `truncate` + add `line-clamp-2` for a 2-line preview cap).

**Priority**: 🟢 Low effort — add to **FE-B24**.

---

### Global Text Wrap Policy Decision

**Tom's note**: Most text description/notes/body columns across all tables should use text wrap rather than single-line truncation. This is a design-level decision that affects how all tables look.

**Recommended approach**: Define a **global text wrap policy** before FE-B24 ships:
- **Short columns** (IDs, numbers, dates, status badges): Keep truncated/single-line
- **Description/body/notes columns**: Default to `line-clamp-2` (2-line preview) — shows more content without making rows excessively tall
- **Full text**: Available on row click/expand or detail page

Add this decision to the Tom + Architect + UI Designer discussion for the table resizing session, since column width resizing and text wrap are related decisions (wider columns = more text visible without wrapping).

---

---

## � Catalog Page — Right-Align Monetary Columns + Supplier Item Pricing Gap

### Cosmetic Fix: Right-Align Currency Columns

Monetary columns should be right-aligned (standard financial table convention). Currently all catalog table columns are left-aligned (`text-left`).

**Columns to right-align:**

| Tab | Column | Fix |
|---|---|---|
| Pricebook | Current Price | Change `<th>` and `<td>` from `text-left` to `text-right` |
| Labor Rates | Hourly Rate | Change `<th>` and `<td>` to `text-right` |
| Labor Rates | Burdened Rate | Change `<th>` and `<td>` to `text-right` |
| Markups | Current Markup | Change `<th>` and `<td>` to `text-right` |

**Implementation**: Pure CSS change. No backend work. Add to **FE-B24** (trivial, part of catalog polish).

---

### Supplier Items Tab — No Pricing Column (Intentional MVP Deferral, Now a Gap)

**Current columns**: SKU, Name, Description, Status
**Missing**: Price column

**The code comment** in `SupplierItemsPage.tsx` says: *"Read-only list of supplier items synced by background process (Celery). No create/edit actions — MVP scope is view-only."*

**Why no price**: Supplier item pricing lives in the `supplier_item_price` table — a separate versioned price table keyed by `supplier_item_id` + `valid_period`. The page shows the item catalog but not its pricing. This was a deliberate MVP deferral.

**Is it a gap?** Yes — for an owner trying to use the supplier catalog, seeing items with no prices is not useful. They need to know what they paid for materials to set markup correctly.

**Recommended fix**: Add a "Current Price" column to `SupplierItemsPage.tsx` showing the `price_cents` from the active `supplier_item_price` row for each item. The backend API for supplier items may already return this field (check `useSupplierItems` hook response shape). If not, backend needs to JOIN `supplier_item_price` filtered to the current valid period.

**Priority**: 🟡 Important — add to **FE-B24** if backend already returns price data; otherwise a mixed B18+FE-B24 task.

---

---

## ✅ Decision Made: Create Invoice Flow — Full-Page Builder at `/invoices/new`

**Status**: Decision reached by Tom + Architect (2026-07-11). UI Designer to produce design spec before engineering batch is scoped.

**Decision**: The `InvoiceCreateModal` is deprecated as the primary invoice creation surface. Invoice creation becomes a **full-page builder at `/invoices/new`**, mirroring the quote builder (`/quotes/new`) in structure and UX. The modal placeholder remains untouched until the full-page builder batch ships.

**⚠️ FE-B24 scope confirmed**: Do NOT touch `InvoiceCreateModal` in FE-B24. The current minimal modal is an acceptable placeholder.

---

### Full-Page Invoice Builder — Feature Specification

#### 1. Surface & Navigation

| Entry Point | Behavior |
|---|---|
| Invoices list "+ Create Invoice" button | Navigate to `/invoices/new` — blank invoice, no pre-fill |
| Job detail "Convert to Invoice" CTA | Navigate to `/invoices/new?job_id={id}` — pre-populate from job |
| Accepted quote "Create Invoice" CTA (future) | Navigate to `/invoices/new?quote_id={id}` — pre-populate from quote |

- On save: navigate to `/invoices/{new_id}` (invoice detail)
- On cancel: return to previous page (back navigation)

#### 2. Line Item Billing Mode

**Default: Line-item selection**
- All billable items from the linked job are shown as a checklist: time entries + expenses
- Contractor checks/unchecks which items to include on *this* invoice
- Unchecked items remain billable for a future invoice on the same job
- Contractor can also add custom line items (manual entry) beyond tracked items

**Toggle: Progress billing**
- A "Progress billing" toggle switches to percentage-based mode
- Contractor sets the % of the total job value to bill now (e.g., 50%)
- Default % values: 50% deposit / 50% on completion (tenant-configurable in Settings)
- **Phase 2.0**: Named milestone billing (e.g., "Rough-in inspection — 30%") — deferred

#### 3. Payment Terms

Payment terms are set at **three levels** (cascading default):

| Level | Where Set | Overrides |
|---|---|---|
| Tenant default | Settings → Billing → Payment Terms | System default |
| Customer-level default | Customer settings / quote settings | Tenant default |
| Per-invoice | Invoice builder | Customer/tenant default |

**Available terms:**
- Due on Receipt *(system default)*
- Net 15
- Net 30
- Custom due date (opens date picker)

**Simple % split payment schedules** (tenant-configurable):
- Default: 50% deposit on start / 50% on completion
- Tenant can change split percentages during onboarding or in Settings

#### 4. Square Payment Integration (Tenant Opt-In)

**MVP scope**: Pilot integrates with Square via the tenant's own Square account (not Pilot as payment processor). This is an opt-in during tenant onboarding.

| Tenant setting | Behavior |
|---|---|
| Square integration enabled | "Credit card required" flag is available per customer/quote. Contractor manages card collection within Pilot via Square before work begins. |
| Square integration disabled | Payment collection is fully external. Pilot shows no card collection UI. Invoice is informational only. |

**"Credit card required" flag scope:**
- Set at the customer level (default for all work with that customer)
- Overridable per quote
- Relevant especially for maintenance contracts and annual service agreements

**Phase 2.0+**: Pilot as its own payment processor (Stripe or similar). Not MVP.

#### 5. Invoice Builder Sections

The `/invoices/new` page layout (mirrors quote builder structure):

1. **Header** — Customer picker (Combobox), Site picker (Combobox), linked Job (if `?job_id=` param present, read-only)
2. **Billing Mode toggle** — "Select line items" (default) ↔ "Progress billing (%)"
3. **Line Items panel** — Checklist of time entries + expenses from job (if linked); custom line item add row
4. **Payment Terms panel** — Terms dropdown, due date, % split if progress billing selected
5. **Notes panel** — Customer-facing note (appears on invoice PDF); internal memo (not on PDF)
6. **Preview button** — Renders invoice preview before save
7. **Save as Draft / Send** — Two action buttons; "Send" triggers email delivery flow

#### 6. Engineering Batch

- **UI Designer**: Produce design spec for `/invoices/new` full-page builder before batch is scoped
- **Backend additions needed** (new batch — likely B19 or B20):
  - `payment_terms` field on `tenant_settings` table
  - `payment_terms` field on `invoice` table (with tenant default cascade)
  - `square_integration_enabled` flag on `tenant_settings`
  - `card_required` flag on `customer` table
  - `card_required` override on `quote` table
  - `billing_mode` (line_item | progress) + `progress_pct` on `invoice` table
  - API endpoint: `GET /api/v1/jobs/{id}/billable-items` — returns time entries + expenses for invoice pre-fill
- **Frontend batch** (new — FE-B26 or FE-B27): Full-page invoice builder component

**Target**: UI Designer spec first → backend batch → frontend batch. Do not start engineering until spec is complete.

---

---

## 🟡 Shared Component Needed: Searchable/Filterable Select (Combobox)

### What It's Called

The component type is a **Combobox** (also called a "searchable select", "autocomplete select", or "typeahead dropdown"). It combines a text input with a dropdown list:
- User clicks or tabs into the field → dropdown opens showing all options (sorted alphabetically)
- User starts typing → list filters in real time to matching options
- User selects an item from the list → field populates with that value
- If the user clears the field → full list reappears

This is a standard component in every major design system (Headless UI, Radix UI, shadcn/ui).

### Where It's Needed

Every entity picker in the app should use a Combobox instead of a plain `<select>` dropdown. High-priority locations:

| Form | Field | Current Type | Should Be |
|---|---|---|---|
| Add Job modal | Customer picker | `<select>` | Combobox — sorted by name, filterable |
| Add Job modal | Site picker | `<select>` (cascades from customer) | Combobox — filtered by selected customer |
| Edit Job modal | Customer picker | `<select>` | Combobox |
| Edit Job modal | Site picker | `<select>` | Combobox |
| Create Invoice modal | Job picker | `<select>` | Combobox |
| Create Invoice modal | Quote picker | `<select>` | Combobox |
| Create Quote page | Customer picker | (check current implementation) | Combobox |
| Create Quote page | Site picker | (check current implementation) | Combobox |
| Dispatch Board — assign job | Tech picker | (check current) | Combobox |

### Implementation Recommendation

**Build one shared `<CustomerCombobox>` and `<SiteCombobox>` in `packages/ui/`** (or `apps/web/src/components/`). These are the two most reused pickers. Rather than re-implementing the combobox logic 8 times, make them purpose-built with:
- Pre-wired to their respective `GET /api/v1/customers/` and `GET /api/v1/sites/?customer_id=` queries
- Alphabetically sorted by `display_name`
- Filterable by text input
- Accepts `value`, `onChange`, `disabled`, optional `customerId` (for site cascade)

**Library recommendation**: `@headlessui/react` Combobox component — it's likely already installed (check `package.json`). Headless UI Combobox is WAI-ARIA compliant, keyboard navigable, and works with Tailwind CSS with no additional CSS framework.

**Target batch**: Add `<CustomerCombobox>` and `<SiteCombobox>` shared components as part of **FE-B25** (where `JobFormModal` and `JobEditModal` both need them), then reuse in FE-B24 (Invoice Create) and beyond.

**Priority**: 🟡 Important — without this, entity pickers become unusable at scale (imagine scrolling through 200 customers in a plain `<select>`).

---

---

## 🔴 "Convert to Invoice" — Two Bugs, Both Broken

### Bug 1: "→ Invoice" Link in Job List Does Nothing Useful

**File**: `JobsPage.tsx` line 101

**Code**: `href={`/jobs/${job.id}?action=convert`}`

The "→ Invoice" action link in the jobs list navigates to `/jobs/{id}?action=convert`. However, `JobDetailPage.tsx` **never reads the `?action=convert` query param** — it simply renders the normal job detail page. The query param is silently ignored. Result: clicking "→ Invoice" from the job list is functionally identical to clicking "View" — it just opens the job detail page with no conversion behavior.

**Fix**: Either:
- (A) Have `JobDetailPage` read `useSearchParams()` for `action=convert` and auto-trigger the invoice creation mutation on mount — but this is dangerous (auto-triggers without confirmation)
- (B) **(Recommended)** Remove the `?action=convert` query param from the link and instead link directly to `/jobs/{id}` with a clear label change. The "Convert to Invoice" button on the detail page is the correct UX entry point — the list link should just say "View" for completed jobs, or open the detail page where the button is visible.

**Priority**: 🔴 Critical — misleads users. Add to **FE-B25**.

---

### Bug 2: "Convert to Invoice" Button Never Visible on Job Detail Page

**File**: `JobDetailPage.tsx` line 80

**Code**: `const showConvertButton = job ? isTerminalStatus(job.status_id) : false;`

`job.status_id` is a **UUID** (e.g. `3f4a...`). The `TERMINAL_STATUSES` Set contains strings like `"completed"`, `"status-completed"`, `"invoice_pending"` — none of which ever equal a UUID string. So `isTerminalStatus(uuid)` always returns `false`, and `showConvertButton` is always `false`. The "Convert to Invoice" button at the bottom of the page is permanently hidden.

**Root cause**: Same as the status badge bug and the status filter bug in `JobsPage.tsx` — `JobResponse` from the API returns `status_id` (UUID) but the code needs `status_code` (human-readable string like `"completed"`).

**Fix**: Once B18 adds `status_code` to `JobResponse`, change line 80 to:
```tsx
const showConvertButton = job ? isTerminalStatus(job.status_code) : false;
```
This is part of the same B18 backend fix + FE-B25 component update that fixes the status badge.

**Priority**: 🔴 Critical — the entire invoice conversion workflow is broken. Add `status_code` to `JobResponse` in **B18**, then fix line 80 in **FE-B25**.

---

### Summary: Invoice Conversion Workflow Status

| Step | Expected Behavior | Actual Behavior |
|---|---|---|
| Job list "→ Invoice" link | Open job detail with Convert to Invoice button visible | Opens job detail; `?action=convert` param is ignored |
| Job detail "Convert to Invoice" button | Visible when job is `completed` or `invoice_pending` | **Never visible** — `isTerminalStatus(uuid)` always false |
| Button action | Creates invoice from job, navigates to `/invoices/{new_id}` | N/A — button never shown |

**Both bugs fix together when B18 adds `status_code: str` to `JobResponse`.**

---

---

## 🔴 Seed Data Gap: Reporting Scenario Has No Invoices for Completed Jobs

**File**: `backend/migrations/scripts/seed_scenario_reporting.py`

**Problem**: The reporting scenario creates 4 completed jobs (Panel Upgrade, Service Call, Commercial Inspection, Outlet Installation) with time entries and expenses — but **no invoices**. This means:
- The Invoices list page shows no entries from the reporting scenario
- The AR aging widget on the dashboard has no data
- The profitability-to-billing connection cannot be demonstrated end-to-end
- The "Convert to Invoice" workflow cannot be validated with existing seed data

**Conceptual note on whether completed jobs always need invoices**:

Not always — the system supports:
- **Warranty work** — no charge, no invoice
- **Internal maintenance** — no customer, no invoice
- **Jobs from non-billable contracts** — invoice handled externally

However, for the **test/demo environment**, every completed job in the reporting scenario represents a billable electrical service call and should have a linked invoice. The "Convert to Invoice" button on job detail is the trigger in the real workflow. The seed data should skip that UI button and create the invoice directly.

**What needs to be added to `seed_scenario_reporting.py`**:

For each of the 4 completed jobs, add an invoice insert after the job is created:

| Job | Invoice Amount | Status | Due Date |
|---|---|---|---|
| Panel Upgrade — Job A (30 days ago) | ~$1,350 (labor + materials w/ markup) | `paid` | 20 days ago |
| Service Call — Job B (45 days ago) | ~$280 (labor + materials w/ markup) | `paid` | 35 days ago |
| Commercial Inspection — Job C (60 days ago) | ~$900 (labor + materials + permit) | `issued` (outstanding) | 5 days ago |
| Outlet Installation — Job D (15 days ago) | ~$240 (labor + materials w/ markup) | `draft` | 5 days from now |

**Mix of statuses** is intentional — gives realistic AR aging: some paid, one issued/outstanding (will show as overdue), one draft (just finished). This drives meaningful data in the dashboard AR aging widget.

**Backend task**: Python Engineer to update `seed_scenario_reporting.py` to:
1. Look up `invoice_status` IDs for `draft`, `issued`, `paid` codes
2. For each seeded job, INSERT into `invoice` table with: `tenant_id`, `customer_id`, `site_id`, `job_id`, `status_id`, `invoice_number` (generated), `issued_at`, `due_at`, `subtotal_cents`, `tax_cents`, `total_cents`, `balance_due_cents`, `currency='USD'`
3. For `paid` invoices: also INSERT into `payment` table
4. Update `mode_reset()` to also delete invoices and payments for these jobs
5. Update `mode_inspect()` to show invoice counts

**Target batch**: Add to a new Python Engineer seed data patch batch (or extend B18 backend scope if convenient).

**Priority**: 🔴 Critical for demo — without invoices, the AR aging, invoice list, and billing widgets are all empty.

---

---

## � Dispatch Board — Filter Panel UX Improvements

**Location**: Dispatch Board page — left-side filter panel containing Tech, Status, Customer, Job Type, and Priority filters.

### Change 1: Collapsible/Expandable Filter Sections

Each filter group heading (Tech, Status, Customer, Job Type, Priority) should be a clickable accordion toggle — click the heading to collapse/expand that section's options. Default state: all expanded.

**Why**: As more filter options are added (more techs, more statuses), the filter panel will grow long. Collapsible sections let owners hide filters they don't use.

**Implementation**: Pure frontend, no backend work. Add `expanded` boolean state per filter group, toggle `chevron-down`/`chevron-up` icon on the heading, animate height with CSS transition or conditional render. Standard accordion pattern.

**Target batch**: FE-B26 (dispatch board multi-view redesign batch) or FE-B24 if the scope fits.

---

### Change 2: Rename "Customer" Filter → "Customer Type"

The filter labeled "Customer" should be renamed to **"Customer Type"** to clarify that this filter is filtering by the type of customer (e.g. Residential, Commercial, Industrial) — not by customer name/individual.

**Implementation**: Pure text label change. One string in the dispatch board filter panel component. No backend work.

**Target batch**: FE-B24 (trivial — part of the sortable headers / polish pass).

---

---

## ✅ Decision Made: Dispatch Board — View Structure (Day / Week / Month)

**Status**: Decision reached by Tom + Architect (2026-07-11). Validated against Jobber, ServiceTitan, and Housecall Pro. UI Designer to produce design spec for Week and Month views before engineering batch is scoped.

**Competitive research summary** (conducted 2026-07-11):

| Competitor | Day | 4-Day | Week | Month | Notes |
|---|---|---|---|---|---|
| **Jobber** | ✅ drag+drop | ✅ mobile only | ✅ drag+drop | ✅ calendar | No desktop 4-day view |
| **ServiceTitan** | ✅ drag+drop | ✅ on calendar | ✅ 5-day or 7-day dispatch board | ✅ calendar | Week IS a full dispatch surface |
| **Housecall Pro** | ✅ drag+drop | ❌ | ✅ Mon-Fri or 7-day | ✅ calendar | No 4-day view |

**Key finding**: No major competitor has a "4-day" view as a primary dispatch surface. All three offer Day + Week + Month. Week view is a full drag-and-drop dispatch surface in all three (not read-only).

---

### Decided View Structure

| View | Keep / Drop | Layout | Interaction |
|---|---|---|---|
| **Day** | ✅ Keep (already redesigned in MKT-B11) | Lane rows per tech — existing | Drag-and-drop |
| **Week** | ✅ Keep — redesign to match Day | Tech-as-column dispatch board | Drag-and-drop |
| **Month** | ✅ Keep — redesign as calendar grid | Standard calendar: day cells with job counts | Click day → drills to Day view |
| **4-Day** | ❌ Drop entirely | N/A | N/A |

---

### Week View — Detailed Spec

**Layout**: Tech-as-column dispatch board. Each column = one technician. Each row = one day (Mon–Fri default; Sun–Sat on 7-day toggle).

**Navigation:**
- **Default**: Mon–Fri of the current week (5 columns × 5 tech rows)
- **7-day toggle**: Sun–Sat of the current week
- **Prev / Next week buttons**: navigate backward and forward one full week at a time
- **"Today" / "This Week" jump button**: returns to current week from any other week

**Interaction:**
- Drag-and-drop job cards between day cells and tech columns — same drag-and-drop model as Day view
- Fixed minimum column width per day (does not compress below minimum — `min-width` per column, `overflow-x: auto` on board container, consistent with Day view constraint documented in this doc)
- Clicking a job card opens the job properties panel (same as Day view)

**Consistency with Day view:**
- Same `schedule_lanes` subscription tier enforcement — if tenant has N lanes, the week view respects that capacity constraint per day cell
- Same job card visual design
- Same color coding by tech / status

---

### Month View — Detailed Spec

**Layout**: Standard 6-row × 7-column calendar grid (Sun–Sat columns). Each day cell shows:
- Day number
- Count of scheduled jobs (e.g., "4 jobs")
- Up to 2–3 abbreviated job chips (tech name + job title, truncated) — remaining count shown as "+N more"

**Navigation:**
- Prev / Next month buttons
- "Today" jump button returns to current month

**Interaction:**
- Read-only — no drag-and-drop at month level
- Clicking any day cell navigates to the **Day view** for that date
- Clicking a job chip opens the job detail page

**Purpose:** High-level capacity planning overview — identify open days, heavy booking periods, upcoming jobs at a glance.

---

### Engineering Notes

**Existing `DispatchGrid` component**: The old grid-style layout still powering 4-Day, Week, and Month views must be replaced/deprecated as part of this batch. The new Week view should reuse Day view's lane/card components wherever possible.

**Engineering batch**: New dedicated batch — **FE-B26** (after FE-B24 and FE-B25 ship). UI Designer spec required before batch is started.

**Do not start any engineering work on Week or Month views until UI Designer has produced the design spec.**

---

---

## 🔴 Job Detail Header — Three Display Bugs (All UUIDs, No Human-Readable Text)

Source file: `JobDetailHeader.tsx`

### Bug 1: Breadcrumb Shows Raw Job UUID

**Line 76**: `<span className="text-neutral-900 font-medium">Job {jobId}</span>`

The breadcrumb shows "Job 3f4a..." (the URL path UUID). Once B18 adds `job_number` to the schema, this should render as "Job JOB-20260710-XYZ".

**Fix**: After B18 adds `job.job_number`, change line 76 to:
```tsx
<span className="text-neutral-900 font-medium">
  {job?.job_number ?? `Job ${jobId.slice(0, 8)}…`}
</span>
```
Add to **FE-B25** (reads `job` data which is already loaded by the hook).

---

### Bug 2: Status Badge Receives UUID Instead of Status Code

**Line 81**: `<StatusBadge statusId={job.status_id} />`

`job.status_id` is a UUID (e.g. `3f4a...`). The `StatusBadge` function tries to strip a "status-" prefix from it and capitalize it, which produces garbled text. The status colors don't apply because none of the UUID keys match the `colorMap`.

**Root cause**: `JobResponse` from the API only returns `status_id` (UUID). It does NOT return `status_code` (the human-readable string like "in_progress"). The `JobListItem` response DOES have `status_code` from its JOIN, but `JobResponse` (single job detail) does not.

**Fix options**:
- **Option A** (backend, recommended): Add `status_code: str` to `JobResponse` schema via JOIN — same pattern already done for `JobListItem`. Add to **B18**.
- **Option B** (frontend): Fetch the job statuses lookup (`GET /api/v1/jobs/statuses` if it exists) and map UUID → code client-side.

**Recommended**: Option A — add `status_code` to `JobResponse` in B18. Then change line 81 to `<StatusBadge statusCode={job.status_code} />` with string-based color map.

**Priority**: 🔴 Critical — status badge renders garbage text today.

---

### Bug 3: Site Shows Raw UUID Instead of Site Name

**Line 85**: `<span className="text-sm text-neutral-500">Site: {job.site_id}</span>`

`job.site_id` is a UUID. The site name (e.g. "The Smith Home", "123 Main St") is on the `site` table as `site.name` or `site.address`. The `JobResponse` schema does not include site name — the frontend would need to either fetch it separately or have the backend include it.

**Fix options**:
- **Option A** (backend, recommended): Add `site_name: str | None` to `JobResponse` — same JOIN pattern as `customer_name` on `InvoiceSummary` in B18.
- **Option B** (frontend): Fetch site detail separately (`GET /api/v1/sites/{id}`) and resolve the name client-side.

**Recommended**: Add `site_name` and `customer_name` to `JobResponse` in B18 while we're already touching that schema. Then line 85 becomes `<span>Site: {job.site_name}</span>`.

**Priority**: 🔴 Critical — "Site: 3f4a..." is meaningless to users.

---

### Summary — What the Job Detail Header Should Show After Fixes

| Element | Current (broken) | After Fix |
|---|---|---|
| Breadcrumb | `Job 3f4a-...` (UUID) | `Job JOB-20260710-XYZ` (job_number) |
| Status badge | Garbled text from UUID cleanup | "In Progress" / "Scheduled" / etc. from `status_code` |
| Site | `Site: 3f4a-...` (UUID) | `Site: The Smith Home` (site name) |
| Customer | ❌ Not shown at all | Should show customer name |
| Quote link | ❌ Not shown at all | `Quote: Q-001 →` (clickable link) |

All five header element fixes map to **B18** (backend schema additions) + **FE-B25** (header component update).

---

---

## Notifications Page — Current State

**What the notifications page shows** (it is NOT a table — it is a card list):

Each notification renders as a clickable card with:
- **Blue dot** indicator (unread only)
- **Body text** — the notification message (e.g. "Your quote Q-001 was approved")
- **Timestamp** — `created_at` formatted as a locale date/time string
- Clicking a card marks it read

Page-level elements:
- "Notifications" header with unread count badge (e.g. "3 unread")
- "Mark all read" button (visible only when unread count > 0)

**What's NOT shown per card**: category/type label, severity, linked entity (job/quote/invoice), action link/CTA. These fields exist in the DB but aren't rendered.

**Potential improvements** (log for review):
- Add a notification **type/category chip** (e.g. "Invoice", "Quote", "System") per card so the user knows at a glance what domain it relates to
- Add a **deep link CTA** so the user can click through to the related entity (e.g. "View Invoice" button on an invoice notification)
- These are 🟡 Important — Phase 1.5 improvements, not critical blockers

---

## Catalog Page — Sortable Column Headers

### 🟡 All Catalog Tabs Need Sortable Headers

All four catalog tabs currently have static `<th>` headers. All sorting should be client-side (data is already loaded into memory on each tab).

| Tab | Columns to Make Sortable |
|---|---|
| **Pricebook** | SKU, Name, Description, Current Price, Status |
| **Labor Rates** | Skill Level, Hourly Rate, Burden %, Burdened Rate, Effective From |
| **Markups** | Category, Current Markup, Effective From |
| **Supplier Items** | SKU, Name, Description, Status |

**Implementation**: Same pattern as all other list pages — `sortField` + `sortDirection` state, `<button>` column headers with ▲/▼ indicators, `.sort()` on in-memory data before render. No backend changes.

**Priority**: 🟡 Important — add to **FE-B24** along with other sortable header work.

---

## Comms Page — Sortable Headers + Search Box

### 🟡 Comms Page Needs Column Sort + Message Search

**Sortable headers**: All columns on the comms thread list should be sortable. Client-side, same pattern as other pages.

**Search box**: A text search input to filter threads/messages by customer name or message content. This is more valuable on comms than on most pages because owners are frequently looking for a specific customer conversation.

**Implementation options**:
- **Client-side** (simpler): Filter the already-loaded thread list by customer name or body text snippet. No backend change.
- **Server-side** (better for large accounts): Add `?search=` param to `GET /api/v1/comms/threads/` (backend change needed). Recommended for production use.

**Priority**: 🟡 Important for client-side version — add to **FE-B24**. Server-side search is Phase 1.5.

---

## Invoice Page — All Columns Sortable

*(Updating previous entry)*

**All four invoice columns** should have sortable headers: Invoice #, Customer, Status, Due. Client-side sort. Add "Total" column (already in API) at the same time.

**Priority**: 🟡 Important — add to **FE-B24**.

---

---

## Table Sortability + Quote Number Gaps

### Current Column Inventory by Page

| Page | Columns Currently Shown |
|---|---|
| **Jobs** | Customer, Status, Scheduled, Actions |
| **Customers** | Name, Type, Email, Actions |
| **Quotes** | Quote ID *(raw UUID — meaningless)*, Customer, Status, Total, Actions |
| **Invoices** | Invoice # *(auto-generated, e.g. INV-20260710-ABC)*, Customer, Status, Due |

---

### 🔴 Missing: `quote_number` — Quotes Show Raw UUID Instead of Human-Readable Number

**Current**: "Quote ID" column shows the UUID (`3f4a...`). This is the internal DB PK — not useful to users.

**Needed**: `quote_number` auto-increment field on `quote` table (e.g., Q-001, Q-002) — same concept as `invoice_number` (already built) and `job_number` (to be added in B18).

**Backend change**: Add `quote_number VARCHAR NOT NULL UNIQUE` to `quote` table in B18. Auto-generate on create (sequence or tenant-scoped counter). Update `QuoteCreate`, `QuoteResponse`, `QuoteListItem` schemas.

**Frontend change**: Replace "Quote ID" column header → "Quote #". Render `quote.quote_number` instead of UUID slice. Add to FE-B24.

**Priority**: 🔴 Critical — add to **B18** (backend) and **FE-B24** (frontend).

---

### 🟡 Missing: Sortable Column Headers on All List Pages

All list pages have static `<th>` headers — no click-to-sort. All current data sorting is done client-side (no sort params sent to backend). This is a **pure frontend** change on each list page.

| Page | Columns to Make Sortable |
|---|---|
| **Jobs** | Customer, Status, Scheduled |
| **Customers** | Name, Type, Email |
| **Quotes** | Quote # *(after B18 adds it)*, Customer, Status, Total |
| **Invoices** | Invoice #, Customer, Status, Due |

**Implementation pattern** (same for all pages):
- Column header becomes a `<button>` with sort indicator (▲ / ▼ / unsorted)
- Track `sortField` + `sortDirection` in component state
- Sort is **client-side** — the existing data already in memory is sorted via `.sort()` before render
- No backend changes needed (all lists are loaded in full or paginated into client memory already)
- Exception: If the invoice list is large enough that server-side sort would be better — this is a future optimization. For MVP, client-side sort is sufficient.

**Priority**: 🟡 Important — add as a task to **FE-B24** (covers all 4 pages in one batch since the pattern is identical).

---

### 🟡 Invoice List — Missing "Total" Column

**Current columns**: Invoice #, Customer, Status, Due
**Missing**: Total amount (`total_cents`) — this is the most important financial field on the invoice list. The owner cannot see what each invoice is worth without clicking into it.

**Fix**: Add "Total" column to `InvoicesPage.tsx` table. Data is already in `InvoiceSummary` response (`total_cents` field). Pure FE change — no backend work.

**Priority**: 🟡 Important — add to **FE-B24**.

---

### 🟡 Invoice List — Missing "Issued Date" Column

**Current columns**: Invoice #, Customer, Status, Due
**Missing**: Issued date (`issued_at`) — useful for understanding the AR aging without filtering.

**Fix**: Add "Issued" column to `InvoicesPage.tsx`. Data already in `InvoiceSummary` response. Pure FE change.

**Priority**: 🟢 Lower — add to **FE-B24** if scope allows, otherwise Phase 1.5.

---

---

## Job Profitability Widget — Missing Budget vs. Actual Comparison

### 🟡 Important: Profitability Widget Doesn't Show Quoted Budget for Comparison

**Current state** (`JobProfitabilityWidget.tsx`): Shows a 3-column grid:
- Actual Labor (`job.actual_labor_cost_cents`)
- Actual Materials (`job.actual_material_cost_cents`)
- Projected Margin % (from `/projected-margin` endpoint)

**What's missing**: No "Quoted" / "Budget" column alongside each Actual column. The owner sees that labor cost is $800 but doesn't know if the quoted labor budget was $600 or $1,200 — they can't tell if they're over or under budget on each line.

**What the backend already returns** from `GET /api/v1/jobs/{id}/projected-margin` (currently unused by the widget):

| Field | Currently shown? | Notes |
|---|---|---|
| `actual_labor_cost_cents` | ✅ | Time entry rollup |
| `actual_material_cost_cents` | ✅ | Job expense rollup |
| `projected_margin_pct` | ✅ | ETC-adjusted margin |
| `quoted_total_cents` | ❌ Not shown | Full quote total — already in response! |
| `quoted_hours` | ❌ Not shown | Quoted labor hours — already in response! |
| `revenue_cents` | ❌ Not shown | Same as `quoted_total_cents` — already in response! |
| `cost_to_date_cents` | ❌ Not shown | Total cost so far (labor + materials) |
| `quoted_labor_cents` | ❌ Doesn't exist | Would require backend change to sum labor-type quote lines |
| `quoted_material_cents` | ❌ Doesn't exist | Would require backend change to sum material-type quote lines |

**Recommended fix (two phases)**:

**Phase 1 — Pure FE, no backend work** (add to FE-B25):
Expand the widget to show the data already in the response:
- Row 1: "Quoted Total" (`quoted_total_cents`) vs "Actual Total" (`cost_to_date_cents`) → delta indicator
- Row 2: "Quoted Hours" (`quoted_hours`) vs "Hours Worked" (`hours_worked`) → delta indicator
- Row 3: Projected Margin % (keep as-is)

**Phase 2 — Backend + FE work** (new batch, lower priority):
Add `quoted_labor_cents` and `quoted_material_cents` to the `/projected-margin` response by summing quote lines by `qco_line_type_id` category. Then the widget can show:
- Quoted Labor vs Actual Labor
- Quoted Materials vs Actual Materials

**Priority**: Phase 1 is 🟡 Important (pure FE, high value, no risk). Phase 2 is 🟢 Phase 1.5 (requires backend work to categorize quote line types).

---

### Test Information

Testing Date: July 10, 2026  
Tester: Tom  
Session: Evening — follow-up to the v1 doc (all v1 items now have batches B18 / FE-B24 / FE-B25)

---

## New Findings from Job Detail Review

### 🔴 Missing: `job_number` — Jobs Have No Human-Readable ID

| Field | Backend | Frontend | Status |
|---|---|---|---|
| `job_number` | ❌ Column does not exist on `job` table (MCP confirmed) | ❌ Job list and detail show raw UUID | **Missing: Schema gap — add to B18** |

**Problem**: Every job is identified only by a UUID. The invoice module generates `INV-20260710-ABC123`. Jobs need `JOB-20260710-XYZ456` or similar. Without this, owners cannot reference a job in conversation with a customer or tech.

**Fix**: B18 backend must add `job_number VARCHAR NOT NULL UNIQUE` to `job` table + auto-generation on create (same pattern as `_generate_invoice_number()` in `invoices.py`).

---

### 🔴 Missing: `quote.title` — Quotes Have No Project Name

| Field | Backend | Frontend | Status |
|---|---|---|---|
| `title` / `project_name` | ❌ Column does not exist on `quote` table (MCP confirmed — only `customer_id`, `site_id`, `status_id`, `expires_at`, etc.) | ❌ Quote list shows customer name only | **Missing: Schema gap — add to B18** |

**Problem**: No way to give a quote a meaningful name (e.g., "Main Panel Upgrade", "Basement Rough-In"). Owners have no way to distinguish multiple quotes for the same customer. Every FSM competitor (Jobber, ServiceTitan) has a job/project title field.

**Fix**: B18 backend must add `title VARCHAR(255) NULLABLE` to `quote` table. Update `QuoteCreate`, `QuoteResponse`, `QuoteUpdate` schemas. FE-B24 must add `title` field to quote create form and display it throughout the app.

---

### 🟡 Missing: Linked Quote Not Displayed on Job Detail

| Surface | Current State | Expected |
|---|---|---|
| `JobDetailHeader.tsx` | Shows status badge, customer name, site, scheduled dates | Should also show "Quote: [quote_number or title] →" as a clickable link to `/quotes/{quote_id}` |

**Problem**: When you open a job, there's no visible link to the originating quote. The `job.quote_id` field exists in the DB but is not surfaced anywhere in `JobDetailHeader.tsx`.

**Fix**: FE-B25 should display the linked quote as a clickable reference in the job detail header.

---

### 🟡 Missing: "Convert to Job" Shortcut on Accepted Quote

| Surface | Current State | Expected |
|---|---|---|
| Quote detail page — accepted status | No "Convert to Job" button | Should show "Create Job from this Quote" button that pre-fills `JobFormModal` with `quote_id` |

**Problem**: When a quote is accepted, the owner has to manually navigate to Jobs, click "Add Job", and separately select the quote. There's no guided conversion flow from the accepted quote. This is the most common next action after quote acceptance.

**Fix**: FE-B24 should add a "Create Job" CTA on accepted quote detail pages that opens `JobFormModal` pre-populated with `quote_id`. *(Note: `JobDetailPage.tsx` already has a "Convert to Invoice" button for terminal-status jobs — the reverse direction is missing.)*

---

## Status of 4 Previously-Asked-About Fields (Not Gaps — Already Built or Intentional)

### 1. `status_id` — Job Status Transitions

**Where it is**: Status is changed via the **Dispatch Board** (drag and drop between lanes). This is intentional by design — the dispatch board is the command center for job scheduling and status management.

**What's visible on job detail**: `JobDetailHeader.tsx` shows the current status as a colored badge (Draft / Scheduled / In Progress / Completed / Invoice Pending). It's read-only on the detail page.

**Is this a gap?**: For MVP — No. The dispatch board is the right place for status transitions. A secondary status dropdown on the job detail page would create conflicting workflow entry points. Post-MVP, an owner may want to force-complete a job from the detail page without going to the dispatch board — that's a Phase 1.5 candidate.

**Verdict**: ✅ Intentional design — not a bug.

---

### 2. Quote Line Items — Not Editable on Job

**Where it is**: Quote line items (scope of work) live on the `quote_version` table as a JSONB snapshot at the time the quote was accepted. Once a job is created, the quote version is frozen.

**How to add scope to an in-progress job**: The **Change Orders** tab on `JobDetailPage.tsx` is the correct mechanism. Change Orders allow adding new line items to a job post-award without modifying the locked quote. This is already built (backend B15 + frontend FE-B21).

**Verdict**: ✅ Works as designed. Change Orders are the correct tool.

---

### 3. Tech Assignment — Not in Job Edit Form

**Where it is**: Tech assignment is managed via the **Dispatch Board** — drag a job card to a technician lane. Tech assignments are stored in `job_tech_assignment` (a separate sub-resource, not a column on `job`).

**What's visible on job detail**: The `JobTimeEntriesTab.tsx` shows which tech logged each time entry (by `user_id`). There is no explicit "Assigned Technicians" tab in the web job detail — that display gap exists but is lower priority.

**Is this a gap?**: The dispatch board is the right assignment surface. However, the job detail page doesn't show who's assigned (only who clocked time). An "Assigned Techs" section in `JobDetailHeader` showing current assignments would be useful — that's a displayonly FE addition (no backend work needed, `GET /api/v1/jobs/{id}/assignments` likely already exists).

**Verdict**: 🟡 Minor display gap — the data exists, just not surfaced on the web job detail page. Phase 1.5 candidate.

---

### 4. Job Notes — Already Fully Built

**Where it is**: The **Notes** tab on `JobDetailPage.tsx` (4th tab). `JobNotesTab.tsx` is a full implementation: auto-saves on blur, shows save status, renders the stored notes from `PUT /{job_id}/notes`.

**Verdict**: ✅ Already complete — no action needed.

---

## Summary Table — All New Issues

| # | Issue | Backend | Frontend | Priority | Target Batch |
|---|---|---|---|---|---|
| 1 | `job_number` — no human-readable job ID | ❌ Missing column + auto-gen | ❌ Display everywhere | 🔴 Critical | Add to **B18** |
| 2 | `quote.title` — no project name field | ❌ Missing column | ❌ Missing from create/list/detail | 🔴 Critical | Add to **B18** |
| 3 | Linked quote not shown on job detail | ✅ `job.quote_id` exists | ❌ Not displayed in `JobDetailHeader` | 🟡 Important | Add to **FE-B25** |
| 4 | No "Create Job" CTA on accepted quotes | ✅ `POST /api/v1/jobs/` exists | ❌ No shortcut from quote detail | 🔴 Critical | Add to **FE-B24** |
| 5 | Status transitions — web job detail only | ✅ | ✅ Dispatch board only — intentional | ✅ By design | No action |
| 6 | Quote line items editable on job | ✅ | ✅ Change Orders tab — intentional | ✅ By design | No action |
| 7 | Tech assignment in job edit | ✅ dispatch board | 🟡 Not displayed on job detail page | 🟡 Low | Phase 1.5 |
| 8 | Job notes | ✅ | ✅ Already built — Notes tab | ✅ Complete | No action |

---

## Dashboard Bug Fixed (This Session)

| Bug | Root Cause | Fix Applied |
|---|---|---|
| `Each child in a list should have a unique "key" prop` on `RecentCustomerMessagesWidget` | Frontend interface declared `message_id: string` which doesn't exist in `RecentMessageItem` backend response; `msg.message_id` was always `undefined` at runtime — every `<li>` got `key={undefined}` | Fixed `useRecentCustomerMessages.ts` interface to match actual backend shape (`thread_id` is the unique key); changed `<li key={msg.message_id}>` → `<li key={msg.thread_id}>` in `RecentCustomerMessagesWidget.tsx`; fixed `received_at` → `last_message_at` field name mismatch |

---

*This document is the active tracking file for Round 2 alpha testing. Add new issues below as discovered.*
