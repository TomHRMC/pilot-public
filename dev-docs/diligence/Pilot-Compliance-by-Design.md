# Compliance by Design — as architected

*The regulatory controls this build designed in from the start. It's capability evidence — proof I build for regulated domains deliberately — not a compliance attestation: the platform never operated with real customers, so nothing here is audited or certified. Implemented vs. aspirational is marked. This is an engineering description, not legal advice.*

---

## Telephony & SMS — TCPA + CTIA 10DLC (built)
A regulated area handled end-to-end rather than hand-waved:
- **10DLC brand/campaign provisioning** — tenant registration flow (`api/routes/tenant_10dlc_profile.py`, `messaging_provisioning.py`) through the Telnyx path, with a **proven 10DLC carrier loop**: the platform campaign was approved under the brand and real texts were delivered to my own phone.
- **Consent capture** — opt-in/consent fields modeled on the contact/communications records (`app/models/communications.py`, `crm.py`, `core.py`); messaging is consent-gated.
- **STOP / START / HELP automation** — keyword handling in the carrier layer (`services/telnyx_sms_carrier.py`) so opt-out is honored automatically.
- **Per-tenant SMS-compliance microsites** — each tenant gets a compliance page (privacy/terms/opt-out) at a wildcard domain, as carriers increasingly expect.

## Payments — PCI-DSS (scoped by architecture)
- Card data is captured and vaulted by **Stripe** via **Payment Intents / Connect**; the application persists **Stripe object references and tokens, not card numbers**. That integration pattern is intended to keep PCI scope to **SAQ A or A-EP**, depending on the final checkout integration; no SAQ has been completed.
- *Aspirational / operating-business step:* a formal PCI **SAQ attestation** is not done — it's a step an operating business completes once it processes real customer volume, which this build never did.

## Privacy & data lifecycle
- **Audit event logging** across the route layer — a record of who did what.
- **PII handling** — a dedicated anonymizer (`services/pii_anonymizer.py`) for de-identification paths.
- **Data portability / export** — a data-export compiler and pipeline (`services/data_export_compiler.py`, `tasks/data_export_pipeline.py`) — the engine a DSAR/"export my data" request would run on.
- **Draft legal pages** — privacy policy, terms, EULA and SMS terms exist in the marketing site (`frontend/apps/marketing/src/app/legal/`); none has had legal review.
- *Aspirational / operating-business steps:* a DPA with sub-processors, formal data-retention schedules, self-serve export/deletion endpoints, and a complete DSAR intake workflow are not built here.

## Honest status
Every control above is **architected and, where noted, implemented** — but none is **audited, attested, or legally reviewed**, and the platform never processed real customer data. The compliance *design* is in place; the compliance *operations* (audits, legal docs, retention enforcement) are deliberately out of scope for a lab build.

## What this demonstrates
I chose a domain that is regulated on three axes at once — telephony (TCPA/10DLC), payments (PCI), and customer-data privacy — on purpose, and built the controls in from day one rather than bolting them on later. Designing compliance in, and being precise about the line between *designed*, *implemented*, and *attested*, is exactly the judgment a fractional CTO brings to a company that can't afford a compliance misstep.
