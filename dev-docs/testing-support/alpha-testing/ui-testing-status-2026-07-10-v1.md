## CRUD UI & API Gap Analysis — Customer, Job, Quote, Invoice

### Test Information

Testing Date: July 10, 2026
Tester: Tom

---

### 🟢 Customer — Mostly Complete

| Operation | Backend API | Frontend UI | Status |
|---|---|---|---|
| List | `GET /api/v1/customers/` ✅ | `CustomersPage.tsx` ✅ | **Complete** |
| Create | `POST /api/v1/customers/` ✅ | `CreateCustomerModal.tsx` ✅ "Add Customer" button | **Complete** |
| View | `GET /api/v1/customers/{id}` ✅ | `CustomerOverviewTab.tsx` ✅ | **Complete** |
| Edit | `PATCH /api/v1/customers/{id}` ✅ | `CustomerOverviewTab.tsx` ✅ inline "Edit Customer" toggle | **Complete** |
| Delete | `DELETE /api/v1/customers/{id}` ✅ | ❌ No delete button/modal anywhere | **Missing: Delete UI** |
| Site Create | `POST /api/v1/sites/` ✅ | `SiteListPanel.tsx` ✅ | **Complete** |
| Site Edit | `PATCH /api/v1/sites/{id}` ✅ | `SiteListPanel.tsx` ✅ | **Complete** |

---

### 🔴 Job — Severely Incomplete

| Operation | Backend API | Frontend UI | Status |
|---|---|---|---|
| List | `GET /api/v1/jobs/` ✅ | `JobsPage.tsx` ✅ with filter pills | **Complete** |
| **Create** | `POST /api/v1/jobs/` ✅ | ❌ **No "Add Job" button** — empty state says "Jobs appear from dispatch board" | **🔴 Missing: Create UI + `useCreateJob` hook** |
| View | `GET /api/v1/jobs/{job_id}` ✅ | `JobDetailPage.tsx` ✅ | **Complete** |
| **Edit** | ❌ `PATCH /api/v1/jobs/{job_id}` **does not exist** | ❌ No edit button/form in detail header | **🔴 Missing: Backend endpoint + Edit UI** |
| Delete | ❌ `DELETE /api/v1/jobs/{job_id}` **does not exist** | ❌ No delete button | **Missing (post-MVP)** |

**`JobCreate` payload**: `{ customer_id, site_id, quote_id?, scheduled_start_at?, scheduled_end_at?, estimated_duration_minutes? }`

---

### 🟡 Quote — Partially Complete

| Operation | Backend API | Frontend UI | Status |
|---|---|---|---|
| List | `GET /api/v1/quotes` ✅ | `QuotesPage.tsx` ✅ | **Complete** |
| Create | `POST /api/v1/quotes` ✅ | `QuoteCreatePage.tsx` ✅ at `/quotes/new` | **Complete** |
| View | `GET /api/v1/quotes/{id}` ✅ | `QuoteDetailPage.tsx` ✅ | **Complete** |
| **Edit (metadata)** | `PATCH /api/v1/quotes/{id}` ✅ accepts `status_id, expires_at, subtotal_cents, tax_cents, total_cents, currency` | The "Edit" link on draft quotes goes to the **detail page** — no standalone edit form for metadata fields like `expires_at` or `currency` | **🟡 Partial: backend exists, no edit form wired** |
| Line item edit | `PATCH /api/v1/quotes/{id}/pending-edits/{edit_id}` ✅ | Inline `LineItemEditor` ✅ in draft mode | **Complete** |
| Approve/Reject/Kickback | All endpoints ✅ | `QuoteActionBar.tsx` ✅ | **Complete** |
| Delete | ❌ No `DELETE /api/v1/quotes/{id}` | ❌ No delete button | **Missing (post-MVP)** |

---

### 🟡 Invoice — Create Modal Has Zero Fields

| Operation | Backend API | Frontend UI | Status |
|---|---|---|---|
| List | `GET /api/v1/invoices/` ✅ | `InvoicesPage.tsx` ✅ | **Complete** |
| **Create** | `POST /api/v1/invoices/` ✅ accepts `quote_id, job_id, customer_notes, terms_and_conditions, due_at, issued_at` | ❌ Modal exists but fires with **zero form fields** — creates a blank invoice with no customer, no due date, no linkage | **🔴 Severely incomplete: modal needs customer picker, quote/job linkage, due date** |
| View | `GET /api/v1/invoices/{invoice_id}` ✅ | `InvoiceDetailPage.tsx` ✅ | **Complete** |
| **Edit** | ❌ `PATCH /api/v1/invoices/{id}` **does not exist** | ❌ No edit UI | **Missing: Backend endpoint + Edit UI** |
| Send | `POST /api/v1/invoices/{id}/send` ✅ | Send button ✅ | **Complete** |
| Record Payment | `POST /api/v1/invoices/{id}/record-payment` ✅ | `RecordPaymentModal.tsx` ✅ | **Complete** |
| **Customer Name** | `GET /invoices/` returns `customer_id` only | Invoice list shows raw UUID (`customer_id.slice(0,8)…`) — no `customer_name` | **🔴 Bug: no customer name in invoice list** |
| Void/Delete | ❌ No backend endpoint | ❌ No UI | **Missing (post-MVP)** |

---

## Prioritized Work Needed for Architect

### 🔴 Critical (blocks demo useability)

1. **Job — Add Job UI**: "Add Job" button in `JobsPage.tsx` + `JobFormModal` (customer select → site cascade → start/end datetime). New `useCreateJob` hook. Backend endpoint already exists.

2. **Invoice — Create Modal Rework**: Replace zero-field modal with a proper form: customer picker, optional quote/job linkage dropdowns, `due_at` date, `issued_at` date, customer notes. Backend endpoint already exists.

3. **Invoice — Customer Name Display**: Invoice list displays truncated UUID. Either backend must add `customer_name` to `GET /api/v1/invoices/` response, or frontend must join via customer lookup.

### 🟡 Important (owner workflow gaps)

4. **Job — Edit UI**: Needs new backend `PATCH /api/v1/jobs/{job_id}` endpoint first (Python Engineer task), then `useUpdateJob` hook + edit form in `JobDetailHeader.tsx` (reschedule dates, reassign customer/site).

5. **Quote — Edit metadata form**: `PATCH /api/v1/quotes/{id}` backend exists. Need `useUpdateQuote` hook + a small edit modal for `expires_at`, `currency`, basic info on the quote detail page.

### 🟢 Post-MVP / Lower Priority

6. Customer delete confirmation modal (backend endpoint exists)
7. Invoice void/cancel (backend endpoint does not exist yet)
8. Quote delete (backend endpoint does not exist yet)
9. Job delete (backend endpoint does not exist yet)