# Pilot for Trades — Product Roadmap

> **📌 Historical snapshot.** Captured June 21, 2026. The Pilot for Trades build was intentionally hibernated in September 2026, so this reflects the product plan *as of that date* — a point-in-time perspective, not a current or committed roadmap.

**Version**: 1.1
**Date**: June 21, 2026
**Author**: Pilot Architect
**Status**: Historical (hibernated September 2026) — was the single source of truth for product phase planning
**Reference**: `mvp-prd.md` for MVP feature specifications | `pilot-fsm-market-gap-analysis-v1.md` for competitive context and GAP-M entries

---

## Version History

| Version | Date | Summary |
| :--- | :--- | :--- |
| 1.0 | June 19, 2026 | Initial creation. Purpose: replace the informal Phase 2 bullet list in PRD §6.2 with a structured, milestone-driven product roadmap that could serve as the single source of truth for all phase planning decisions. Established three phase definitions (MVP 1.0, Post-Launch 1.5, Expansion 2.0) with milestone triggers rather than calendar dates. Incorporated all 18 GAP-M competitive gaps from the FSM market gap analysis. Captured all 8 phase decisions made by Tom (VOIP → Phase 2, Wisetack → MVP, signature capture → MVP, quote follow-up reminder → MVP, Reserve with Google → Phase 1.5 submit / Phase 2 implement, public API → Phase 1.5 design / Phase 2 launch, WIP dashboard → MVP, HVAC flat-rate book → Phase 2). Added Tom-only action items (P0 section). Included Feature-Phase Quick Reference table covering 70+ features as single-row lookup. |
| 1.1 | June 21, 2026 | Multi-vertical architecture additions. Added 5 pre-beta abstraction items to MVP P2: `tenant.vertical_code`, vertical feature flags, per-vertical seed catalog JSON structure, voice AI system prompt per vertical, onboarding wizard vertical selection. These items enable expansion to plumbing, HVAC, and eventually the services vertical without code forks. Phase 2.0 updated to include `pilotforservices.com` services expansion strategy (cleaning, landscaping, handyman). Non-engineering action items table eliminated — Tom's actions merged directly into P0 section and Feature-Phase Quick Reference. Feature-Phase Quick Reference updated with all Tom action items inline. |

---

## Phase Definitions

| Phase | Label | Definition | Milestone Trigger |
|---|---|---|---|
| **Phase 1.0 — MVP** | Current product | All features designed in PRD v3.1.1 + the build gaps and market gaps that must be closed before the first paying customer | Product is demo-ready, core loop works end-to-end, all P0 launch blockers resolved |
| **Phase 1.5 — Post-Launch** | First 60–90 days | Features that prevent churn and close competitive parity gaps in the critical first 90 days of paid use | 10+ active beta customers have completed at least 5 real jobs each |
| **Phase 2.0 — Expansion** | Scale & Trade Expansion | Trade expansion (plumbing, HVAC), platform depth, public API, advanced integrations | 50–100 paying customers on $49/month plan; product-market fit confirmed |

> **Note**: Phases are milestone-driven, not calendar-driven. Phase 2 can begin earlier if product-market fit is confirmed sooner. The "Phase 1.5" label replaces the informal "first 60 days" language used in earlier planning documents. The PRD's §6.2 "Phase 2" references the same scope as Phase 2.0 in this document.

---

## Phase 1.0 — MVP Feature Checklist

### Completed ✅ (as of June 17, 2026 — Batches B17 through MOB-B7)

| Feature | Batch | Notes |
|---|---|---|
| Customer create/edit + site management (web) | FE-B18 | CRM core loop complete |
| Quote builder UI + line items + send flow (web) | FE-B19 | Includes always-preview-before-send |
| Catalog management UI — pricebook, markups, labor rates (web) | FE-B20 | Full CRUD |
| Jobs web module — list, detail, profitability, time/expense/notes | FE-B21 | Dispatch board links to job detail |
| Invoice detail + create + record payment + AR aging (web) | FE-B22 | Invoice detail no longer 404 |
| Dashboard business intelligence — at-risk jobs, AR aging, notifications bell | FE-B23 | Dashboard is now demonstrable |
| Voice AI session list + session detail on web | FE-B23 | `/voice` routes built |
| GPS clock-in on mobile (`expo-location`) | MOB-B6 | Soft-fail on permission denial |
| Photo documentation on mobile (`expo-image-picker`) | MOB-B6 | S3 multipart pipeline |
| Structured voice messages (job ETC, conflict summary) | MOB-B6 | Replaces stub cards |
| LOTO tenant-configurable | MOB-B7 | Gate reads `loto_confirmation_required` setting |
| Create customer on mobile | MOB-B7 | Bottom sheet form |
| Today-first home tab on mobile | MOB-B7 | Jobs are primary content |
| API contract fixes + missing endpoints | B17 | SSE JWT centralized; `useProfitability` fixed |

---

### Remaining MVP Build Items (Must Close Before Beta Launch)

#### P0 — Must Have Before General Availability

These are open "Tom" items that he must complete before Pilot goes to Beta testing.

| Item | GAP Ref | Effort | Owner |
|---|---|---|---|
| Production GPU instance provisioned (`g4dn.xlarge` on AWS) | GAP-M15 | DevOps — Terraform | Tom + DevOps |
| Llama 3.x fine-tuned on electrical vocabulary (~10K patterns) | GAP-M15 | AI engineering | Tom + AI |
| Voice AI pipeline field-validated with real audio (beta contractors) | GAP-M15 | Operational | Tom |
| PilotForTrades.com marketing website deployed and live | Data task | Operational | Tom |
| **Submit** A2P 10DLC brand + campaign registration with Telnyx | External | Operational | Tom |
| **Submit** QuickBooks Intuit production app review | External | Operational | Tom |
| **Apply** Wisetack partner program (partner.wisetack.com) | MVP P2 | Operational | Tom |
| Seed production pricebook with 50+ common electrical service packages | Data task | Data entry | Tom |

#### P1 — Launch Blockers (No Exceptions)

These are open development items that must be completed before Pilot can accept the first paying customer.

| Item | GAP Ref | Effort | Owner |
|---|---|---|---|
| Seed data scripts updates | Roadmap - Data Tasks found in README-seed-data.md | Operational | Python Engr |
| Background sync — server-initiated silent push (FCM + APNS) | GAP-M17 | Backend + Mobile — 1 mixed batch | Python Engr + RN Engr |
| BGAppRefreshTask (iOS) + WorkManager (Android) background task registration | GAP-M17 | Mobile | RN Engr |
| Recurring jobs — basic pattern (daily/weekly/monthly/annually) | GAP-M1 | Backend + FE + Mobile — 1 mixed batch | Python Engr + React Engr |
| Bullet-proof Quickbooks integration - at-scale edge case testing | Competitor Analysis | External | Python & React Engr + Tom |
| Bullet-proof Web & Mobile UI - edge case testing | Competitor Analysis | External | Python & React Engr + Tom |

#### P2 — Must Have Before General Availability (including multi-vertical foundation)

| Item | GAP Ref | Effort | Owner |
|---|---|---|---|
| **`tenant.vertical_code`** — add vertical type to tenant signup (electrical/plumbing/hvac/cleaning/other) | New | Low — 1 migration + AuthContext | Python Engr + React Engr |
| **Vertical feature flags** — `vertical_feature_config` table keying which features are enabled per vertical | New | Low — 2 days total | Python Engr + React Engr |
| **Vertical seed catalog structure** — split pricebook seed into per-vertical JSON files (`catalog_electrical.json`, etc.) | New | Low — 1 day refactor | Python Engr |
| **Voice AI system prompt per vertical** — `vertical_code`-keyed system prompt dict; electrical context for MVP; plumbing/HVAC stubs | New | Low — 0.5 days | Python Engr |
| **Onboarding wizard vertical selection** — add "What type of business?" step to signup wizard; drives catalog seed + feature flags | New | Low — 1 day | Python Engr + React Engr |
| Wisetack consumer financing embed on public invoice page | New | Low — Wisetack React SDK | React Engr |
| Mobile signature capture on invoice sign-off | New | Low — Expo canvas component | RN Engr |
| Quote follow-up automated reminder (N days after send, no customer response) | New | Low — Celery + new SMS template | Python Engr |
| Automated customer service survey / review request post-job close | GAP-M3 | Low — Celery + SMS template | Python Engr |
| WIP dashboard report — all active jobs sorted by budget deviation | New | Low-Medium — new report endpoint + FE | Python Engr + React Engr |
| Appointment reminders settings UI (configurable delay times) | New | Low — settings page addition | React Engr |
| Customer Jobs / Invoices / Quotes tabs on customer detail | FE-B18 deferral | Medium — requires `?customer_id=` filter on API | Python Engr + React Engr |
| Partial payment "Pay remaining" CTA on public invoice page (post-partial payment) | New | Low — FE-B22 follow-up | React Engr |
| Background sync settings UI (tenant + user override) | PRD §3.15 | Low — already designed | React Engr |

---

## Phase 1.5 — Post-Launch Enhancements

Features that close churn-causing gaps within the first 60–90 days of paid usage. Trigger: 10+ beta customers active with 5+ real jobs each.

### 1.5-A: Revenue & Quoting Enhancements

| Feature | GAP Ref | Effort | Priority |
|---|---|---|---|
| **Good/Better/Best tiered quote presentation** | GAP-M4 | Medium-High | 🔴 Critical — competitors report revenue uplift from tiered options |
| Payment method management + self-serve subscription billing UI | GAP-M13 | Medium | 🟡 High |
| Stripe Connect platform model (Pilot as payment processor; earn platform fee) | New | High | 🟡 High (Phase 1.5 or 2 based on compliance review) |

### 1.5-B: Customer Acquisition & Retention

| Feature | GAP Ref | Effort | Priority |
|---|---|---|---|
| **Online booking request form** (customer fills form → owner queue → confirms) | GAP-M2 | Medium | 🔴 Critical — Google "Book" button |
| **Submit Reserve with Google partnership application** *(Tom action item — not engineering)* | New | Operational | 🔴 Critical — submit as soon as GAP-M2 is built |
| **Persistent customer portal** (`pay.pilotfortrades.com/{tenant}/{token}`) | GAP-M6 | Medium | 🟡 High |
| Lead / inquiry capture (pre-customer pipeline) | GAP-M9 | Low-Medium | 🟡 High |
| Referral source tracking on customer records | GAP-M10 | Very Low | 🟢 Medium |

### 1.5-C: Field Operations Improvements

| Feature | GAP Ref | Effort | Priority |
|---|---|---|---|
| **Mobile job forms + checklists** (simple ordered checkboxes; custom form builder in Phase 2) | GAP-M5 | Medium | 🔴 Critical — every competitor has this |
| Deficiency / finding capture → auto-populate follow-up quote | GAP-M7 | Medium | 🟡 High |
| Timesheet export for payroll (weekly/bi-weekly CSV export per tech) | New | Low | 🟡 High |
| Inventory / parts stock tracking (stock on hand + per-job depletion + low-stock alert) | GAP-M18 | Medium | 🟢 Medium |
| Site equipment / asset records (equipment cards — panels, generators, units per site) | GAP-M12 | Medium | 🟢 Medium |

### 1.5-D: Reporting & Analytics

| Feature | GAP Ref | Effort | Priority |
|---|---|---|---|
| **Expanded reporting suite** — revenue by period, tech performance metrics, customer lifetime value | GAP-M14 | Medium | 🔴 Critical |
| Tech performance dashboard — revenue/tech, jobs/tech, avg margin/tech | New (part of GAP-M14) | Low-Medium | 🟡 High |
| Voice AI remaining build gaps — persona tone UI, NEC on web voice, field validation | GAP-M16 | Low-Medium | 🟡 High |

### 1.5-E: Dispatch & Scheduling

| Feature | GAP Ref | Effort | Priority |
|---|---|---|---|
| **Live dispatcher GPS map** (tech pins on map, job markers, click-to-detail) | GAP-M8 | Medium | 🟡 High |
| Route optimization button in dispatch board (Google Routes Preferred API) | New | Low-Medium | 🟡 High |
| Dispatch board month view (currently deferred) | FE-B5 deferral | Low | 🟢 Medium |

### 1.5-F: Platform & Integration

| Feature | GAP Ref | Effort | Priority |
|---|---|---|---|
| Supplier catalog integrations (Rexel, Graybar, City Electric connectors) | New | Medium per connector | 🟡 High |
| Public REST API design + developer documentation | New | Medium (design + auth layer) | 🟡 High |
| Wisetack implementation on web + mobile (if not completed in MVP) | New | Low | 🟡 High |
| Communication templates management UI (browse + customize SMS templates) | FE deferral | Low-Medium | 🟢 Medium |
| Supplier connector configuration UI (api/scrape/manual modes) | FE deferral | Medium | 🟢 Medium |

---

## Phase 2.0 — Expansion

Trigger: 50–100 paying customers; product-market fit confirmed for electrical contractors.

### 2.A: Trade Expansion (Original PRD §6.2)

| Feature | Notes |
|---|---|
| Plumbing trade catalog + code references | Pipe sizing, drain calculations, plumbing material taxonomy |
| HVAC trade catalog + code references | BTU calculation, refrigerant charge, duct sizing |
| Trade-specific calculation modules | HVAC: BTU/load calc; Plumbing: pipe sizing; built into voice AI |
| HVAC flat-rate book (licensed; partner not chosen) | Licensing deal — revisit at 50 customers |
| Pre-built HVAC pricebook from industry standard sources | After partnership secured |

### 2.B: Platform Depth (Original PRD §6.2)

| Feature | Notes |
|---|---|
| Multi-tech crew assignment on jobs | Schema already supports many-to-many; UI update only |
| Bulk conflict resolution (calendar, QB) | Currently per-conflict only |
| Three-way diff with base snapshot visibility | For conflict resolution surfaces |
| Owner-defined auto-resolution rules | Rule engine for conflict auto-expiry |
| Multi-calendar support (Outlook, iCal) | Architecture is provider-abstract; second provider is config |
| Mobile touch resolution UI for sync conflicts | Currently web-only or voice |
| Voice persona tone configuration UI | Already in DB; settings page deferred |

### 2.C: Advanced Monetization

| Feature | Notes |
|---|---|
| Stripe Connect platform model (if not done in Phase 1.5) | Earn 0.5% on payments processed through Pilot |
| Consumer financing program expansion | Wisetack Phase 1; evaluate GreenSky/Financeit for commercial |
| SMS marketing automation campaigns | Similar to Housecall Pro pipeline feature |

### 2.D: Public API + Ecosystem

| Feature | Notes |
|---|---|
| Public REST API implementation (Phase 1.5 = design; Phase 2 = launch) | API key auth, developer portal, rate limiting |
| Zapier integration | Build after public API; leverages existing endpoints |
| Webhook event delivery system | For external integrations to subscribe to Pilot events |
| Reserve with Google integration (Phase 1.5 = apply; Phase 2 = implement) | Full calendar-aware booking from GBP |

### 2.E: Advanced Field Operations

| Feature | Notes |
|---|---|
| Custom job form builder (drag-and-drop) | Phase 1.5 = simple checklists; Phase 2 = full form builder |
| Maintenance agreements + recurring billing | Service contracts with automatic invoice generation |
| Maintenance plan management (HVAC/plumbing focus) | Seasonal tune-up scheduling + billing automation |
| Equipment service history + warranty tracking | Extension of Phase 1.5 equipment cards |
| PDF report generation (professional inspection reports) | Customer-facing leave-behind reports |
| Automated availability-aware self-scheduling | Phase 1.5 = request form; Phase 2 = real availability check |

### 2.F: CRM & Sales Depth

| Feature | Notes |
|---|---|
| AI automated lead response (Filt-style) | AI answers inbound inquiry at 9pm, schedules follow-up |
| Service agreement proposal workflow | Quote-to-contract flow for annual maintenance deals |
| Customer satisfaction surveys + NPS | Step up from review request (Phase MVP) to structured NPS |
| Referral program management | Track referrals, send thank-you bonuses |

### 2.G: Communications & VOIP

| Feature | Notes |
|---|---|
| VOIP integration (Telnyx SIP + WebRTC) | **Evaluate demand in beta first** — only build if beta contractors ask |
| Call recording + transcription | Requires VOIP to be built first |
| Conversation analysis on calls | Requires VOIP + transcription |
| Team chat / internal messaging | Tech-to-dispatcher + tech-to-tech |

### 2.H: Intelligence & AI

| Feature | Notes |
|---|---|
| Local market pricing data (Sera-style AI pricing) | Requires 12–18 months of anonymized transaction data to train |
| Tech performance leaderboards + gamification | Revenue/tech scoring visible to tech + owner |
| AI-assisted diagnostic / upsell suggestions | "Based on panel age, suggest surge protection" |
| Photo-to-quote AI (photograph panel → draft scope) | Direct QuoteIQ competitive response |

### 2.I: Platform Infrastructure

| Feature | Notes |
|---|---|
| Route-based scheduling mode (for cleaning companies) | MotionOps-style; enables cleaning vertical |
| Cleaning vertical (ZenMaid competitive) | Recurring route scheduling, automatic recurring billing |
| Xero integration (AU/NZ/UK market) | After US PMF confirmed |
| Per-event sync exclusions (QB/calendar) | Fine-grained sync control |
| Operator-admin web interface | Currently Tom manages via DB; needs a UI for scale |

---

## Feature-Phase Quick Reference

The table below maps every named feature and GAP-M entry to its phase assignment. Use this as a single-row lookup before any architecture or engineering session.

| Feature / GAP | Phase | Status |
|---|---|---|
| Core business loop (customer/quote/job/invoice/payment) | MVP | ✅ Complete (B17–FE-B23) |
| GPS clock-in + photo documentation | MVP | ✅ Complete (MOB-B6) |
| Dispatch board with conflict detection | MVP | ✅ Complete |
| QuickBooks integration | MVP | ✅ Complete |
| Calendar sync + conflict resolution | MVP | ✅ Complete |
| Voice AI pipeline (local Whisper + Llama) | MVP | 🟡 Code complete; GPU not in prod |
| Offline-first mobile (foreground sync) | MVP | 🟡 Code complete; background sync pending |
| `tenant.vertical_code` — vertical type on tenant | MVP P2 | ❌ Not built |
| Vertical feature flags (`vertical_feature_config`) | MVP P2 | ❌ Not built |
| Vertical seed catalog JSON structure | MVP P2 | ❌ Not built |
| Voice AI system prompt per vertical | MVP P2 | ❌ Not built |
| Onboarding wizard vertical selection step | MVP P2 | ❌ Not built |
| GAP-M1: Recurring jobs | MVP | ❌ Not built — P1 launch blocker |
| GAP-M15: Production GPU deployment + Llama fine-tuning | MVP P0 | ❌ Not done — Tom action |
| GAP-M17: Background sync (silent push) | MVP | ❌ Not built — P1 launch blocker |
| Submit A2P 10DLC registration with Telnyx *(Tom)* | MVP P0 | ⏳ Not submitted |
| Submit QuickBooks Intuit production app review *(Tom)* | MVP P0 | ⏳ Not submitted |
| Apply Wisetack partner program *(Tom)* | MVP P0 | ⏳ Not applied |
| Wisetack consumer financing embed on invoice | MVP | ❌ Not built — P2 MVP |
| Signature capture on mobile | MVP | ❌ Not built — P1 MVP |
| Quote follow-up automated reminder | MVP | ❌ Not built — P1 MVP |
| GAP-M3: Post-job review request / survey | MVP | ❌ Not built — P1 MVP |
| WIP dashboard report | MVP | ❌ Not built — P1 MVP |
| Appointment reminder settings UI | MVP | ❌ Not built — P1 MVP |
| Customer Jobs/Invoices/Quotes tabs on customer detail | MVP | ❌ API filter missing |
| Partial payment "Pay remaining" CTA | MVP | ❌ Verify FE-B22 |
| Background sync settings UI | MVP | ❌ Not built |
| GAP-M4: Good/Better/Best tiered quote | Phase 1.5 | ❌ Not designed |
| GAP-M2: Online booking request form | Phase 1.5 | ❌ Not designed |
| Reserve with Google — **submit application** *(Tom)* | Phase 1.5 | ⏳ Action item for Tom |
| GAP-M6: Persistent customer portal | Phase 1.5 | ❌ Not designed |
| GAP-M5: Mobile job checklists | Phase 1.5 | ❌ Not designed |
| GAP-M7: Deficiency / finding capture | Phase 1.5 | ❌ Not designed |
| GAP-M8: Live dispatcher GPS map | Phase 1.5 | ❌ Not designed |
| GAP-M9: Lead / inquiry capture | Phase 1.5 | ❌ Not designed |
| GAP-M10: Referral source tracking | Phase 1.5 | ❌ Not designed |
| GAP-M12: Site equipment / asset records (panel cards) | Phase 1.5 | ❌ Not designed |
| GAP-M13: Payment method management UI | Phase 1.5 | ❌ Not built |
| GAP-M14: Expanded reporting suite | Phase 1.5 | ❌ Not designed |
| GAP-M16: Voice AI remaining build gaps | Phase 1.5 | ❌ Partially built |
| GAP-M18: Inventory / parts stock tracking | Phase 1.5 | ❌ Not designed |
| Route optimization button (dispatch board) | Phase 1.5 | ❌ Not designed |
| Timesheet export for payroll | Phase 1.5 | ❌ Not built |
| Supplier catalog integrations (Rexel, Graybar) | Phase 1.5 | ❌ Not built |
| Public REST API design | Phase 1.5 | ❌ Not designed |
| Tech performance dashboard | Phase 1.5 | ❌ Not designed |
| Dispatch board month view | Phase 1.5 | ❌ Deferred placeholder |
| Comm templates management UI | Phase 1.5 | ❌ Deferred |
| Supplier connector config UI | Phase 1.5 | ❌ Deferred |
| Stripe Connect platform fee model | Phase 1.5 or 2 | ❌ — compliance review needed |
| GAP-M11: expo-location + expo-image-picker | RESOLVED | ✅ MOB-B6 June 17, 2026 |
| VOIP (Telnyx SIP + WebRTC) | Phase 2 | — Evaluate beta demand first |
| Reserve with Google — full implementation | Phase 2 | — After Phase 1.5 application |
| Public REST API implementation | Phase 2 | — After Phase 1.5 design |
| Zapier integration | Phase 2 | — After public API |
| HVAC flat-rate book (licensed; partner not chosen) | Phase 2 | — BD negotiation required |
| **Begin flat-rate book licensing discussions** *(3–6 month lead time)* | Phase 2 | ⏳ Start at 50 customers |
| Trade expansion: plumbing catalog | Phase 2 | — Original PRD §6.2 |
| Trade expansion: HVAC catalog | Phase 2 | — Original PRD §6.2 |
| Maintenance agreements + recurring billing | Phase 2 | — Original PRD Phase 2 |
| Equipment service history + warranty tracking | Phase 2 | — Extension of GAP-M12 |
| Custom job form builder (drag-and-drop) | Phase 2 | — Phase 1.5 = simple checklist |
| Local market AI pricing | Phase 2 | — Needs 12–18 mo transaction data |
| Photo-to-quote AI | Phase 2 | — Competitive with QuoteIQ |
| Multi-tech crew assignment | Phase 2 | — Schema ready; UI only |
| Team chat / internal messaging | Phase 2 | — Original PRD Phase 2 |
| AI automated lead response | Phase 2 | — Filt-style; complex |
| Consumer financing expansion | Phase 2 | — Beyond Wisetack |
| Xero integration | Phase 2 | — AU/NZ/UK market |
| Cleaning vertical (route-based scheduling) | Phase 2 | — After PMF in trades |

---

## Milestone Definitions

| Milestone | Definition |
|---|---|
| **MVP Complete** | All P0 launch blockers resolved; all P1 MVP items built; product works end-to-end for an electrical contractor with 1–5 employees |
| **Beta Ready** | MVP Complete + seed data + code quality gates + E2E harness (per pre-WS3 prep plan Phase 1 and Phase 2) |
| **General Availability** | 5+ beta contractors have used the product for 30+ days on real jobs; critical bugs resolved |
| **Phase 1.5 Trigger** | 10+ active customers on paid plan with 5+ real jobs each completed |
| **Phase 2 Trigger** | 50–100 paying customers; <5% monthly churn; customer feedback confirms product-market fit for electrical trade |

---

*Document created June 19, 2026. This roadmap supersedes the Phase 2 references in PRD v3.1.1 §6.2 — see that section for the original Phase 2 list. This document is the living roadmap; update it as decisions are made. Cross-reference with `pilot-fsm-market-gap-analysis-v1.md` for competitive context behind each feature decision.*
