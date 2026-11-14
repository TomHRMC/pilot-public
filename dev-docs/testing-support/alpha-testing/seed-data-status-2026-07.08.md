## Live DB Seed State — Post SD-01 through SD-10

Here's a complete inventory of what's in the database and what you can test:

---

### 👥 Customers — 9 rows

| Display Name | Type | Phone | Scenario |
|---|---|---|---|
| John Smith | person | +1-212-555-1001 | Quote-to-cash (primary) |
| Mary Johnson | person | +1-212-555-1002 | Quote-to-cash |
| Apex Commercial LLC | company | — | Quote-to-cash commercial |
| Bob Davis | person | — | Prospect / no jobs |
| Inactive Customer | person | — | Dormant state testing |
| Jane Doe | company | 555-1234 | ⚠️ Non-E.164 — pre-seed leftover |
| Carlos Rivera | person | +1-312-555-1010 | SMS comms — 2 unread |
| Linda Park | person | +1-617-555-1020 | SMS comms — 1 unread |
| Sunrise Electric LLC | company | +1-415-555-1030 | SMS comms |

**Test**: Customer list, search, type badge (person/company), inactive state, SMS opt-in indicators.

---

### 🏗️ Jobs — 13 rows

| Status | Date | Customer |
|---|---|---|
| `completed` | 2026-05-02 | Apex Commercial LLC |
| `completed` | 2026-05-17 | Mary Johnson |
| `completed` | 2026-06-01 | John Smith |
| `completed` | 2026-06-12 | John Smith |
| `completed` | 2026-06-14 | John Smith |
| `in_progress` | 2026-06-15 | John Smith |
| `scheduled` | 2026-06-16 | John Smith |
| `completed` | 2026-06-16 | John Smith |
| `completed` | 2026-07-03 | John Smith |
| `completed` | 2026-07-05 | John Smith |
| `in_progress` | 2026-07-06 | John Smith |
| `scheduled` | 2026-07-07 | John Smith |
| `draft` | *(no schedule)* | John Smith |

**Test**: Dispatch board (2 scheduled, 2 in-progress), job list, status filter, completed history, draft state, job with no schedule date.

---

### 💬 SMS / Customer Comms — 3 threads, 9 messages

| Customer | Messages | Unread |
|---|---|---|
| Carlos Rivera | 4 (mix in/outbound) | ✅ 1 unread inbound |
| Linda Park | 3 | ✅ 1 unread inbound |
| Sunrise Electric LLC | 2 | — |

**Test**: Inbox unread badge (should show **2**), thread view, inbound vs. outbound styling, read/unread state.

---

### 📄 Quotes — 1 row

- **Status**: `draft`
- **Customer**: John Smith → Smith Residence (123 Main St, Brooklyn NY 11201)
- **Line 1**: Standard Outlet × 1 = $150
- **Line 2**: 15A Circuit Breaker × 5 = $90
- **Total**: $240

**Test**: Quote list, quote detail, line item rendering, draft status badge. You **cannot** test `sent`, `approved`, or `accepted` states without creating a new quote and advancing it.

---

### 💰 Invoices — 0 rows

Invoice list will be empty. Cannot test invoice surfaces without creating one via the UI or API.

---

### 📦 Pricebook — 5 items

| Name | Type | Tax |
|---|---|---|
| Standard Outlet Install | labor | taxable |
| 200A Panel Upgrade | labor | taxable |
| 15A Circuit Breaker | material | taxable |
| EMT Conduit | material | taxable |
| Residential Permit Fee | misc | **exempt** |

**Test**: Pricebook list, type filter (labor / material / misc), tax-exempt indicator, item picker on quote create.

---

### 📊 Reporting / Profitability Data

- **7 time entries** — master ($120/hr) + journeyman ($85/hr) rates, 1.5–4 hrs each
- **5 job expenses** — materials + permits, 20% markup applied
- **10 tech assignments** — all assigned to `tech@pilot.local`
- Past-dated completed jobs from May–June 2026

**Test**: Profitability report, time entry breakdown on job detail, expense breakdown, labor cost totals on completed jobs.

---

### 🏭 Supplier Catalog — 1 supplier, 5 items

- **Supplier**: Wesco Distribution
- **Item categories covered**: wire_cable, conduit_raceway, dist_equip, wiring_devices, fittings

**Test**: Supplier list, item list, category filter.

---

### 📋 Platform Config (always present)

| Area | Data |
|---|---|
| Product plans | starter, **teams**, enterprise (SD-07 renamed `professional` → `teams`) |
| Subscription | Pilot Dev Tenant → `enterprise` plan, `active` status |
| Quote templates | 3 system templates available in quote create |
| Labor rates | Master $120/hr, Journeyman $85/hr, Apprentice $55/hr |
| Markup | 20% on materials |

---

### 🔑 Test Login Credentials

| Role | Email |
|---|---|
| Owner (full access) | `dev@pilot.local` |
| Technician | `tech@pilot.local` |
| Office Staff | `office@pilot.local` |

---

### ⛔ What You CANNOT Test Yet

| Surface | Reason |
|---|---|
| Invoices | 0 rows in DB |
| Payments / refunds | 0 rows |
| Discount codes on quotes | `discount_version` = 0 rows — re-run `seed_test_tenant.py` to fix (SD-09 adds `SUMMER_PROMO` + `NEW_CUSTOMER` rows) |
| QuickBooks sync | Requires OAuth + QB sandbox |
| Voice AI sessions | Requires Whisper/Ollama GPU |
| Help chat | No `help_article` corpus (deferred in SD-09) |
| MFA enrollment | No `user_mfa_method` rows |
| Notification history | No `notification_event` rows |

---

### ⚠️ One Discrepancy Found

The live DB shows `discount_version = 0 rows`, but SD-09 completion summary claims 2 rows were added to `seed_test_tenant.py`. This means the script was updated post-SD-09 but the tenant was likely reset without a re-seed. Run:

```bash
cd backend && python migrations/scripts/seed_test_tenant.py
```

to restore the `SUMMER_PROMO` (10% off) and `NEW_CUSTOMER` ($25 off) discount rows before testing the quote discount flow.