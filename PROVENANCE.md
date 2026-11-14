# Provenance — What This Repository Is (and Isn't)

This is a **curated, public snapshot** of *Pilot for Trades*, a full-stack
field-service-management platform Tom Lang architected and built **solo,
AI-augmented, in about six months of full-time build** as a personal
research-and-development build. It is published as a capability and proof asset for **HotRMC**
(fractional-CTO practice).

For *how* it was built, read **METHOD.md**; for the AI failure modes the method
was built to contain, read **AI-PITFALLS.md**. This file covers the provenance
of the artifact itself — where it came from, what's real, and what was changed
or removed to publish it safely.

## What it is — and is not
- A **personal R&D build / lab**, architected to prove a delivery method.
- **Never released; no customers; no real user data.** The AWS environment is
  turned off to save cost. Restarting it is about one day of runbook work; allow
  about a week of calendar time for a demo-ready environment (GPU capacity, DNS,
  carrier and Stripe re-verification). The domain still serves a static hold
  page.
- The technical design follows the **SOC 2 security criteria — built to the
  controls, not audited.** Nothing here is certified, compliant, or
  auditor-reviewed.
- Not a product offered for sale or use. See **LICENSE** (source-available,
  view-only).

## Build provenance (from the private original's git history)
These figures come from the private repository's history. This public snapshot
is a single fresh commit, so they can't be re-derived from it.

- **~6 months of full-time build:** first commit 2026-03-02 -> last 2026-09-07
  (189 calendar days).
- **Before the build:** roughly 4–6 months (from about October 2025) of
  part-time research, market analysis and design concepts, done between other
  work to decide what was realistic and honest to build. Early experiments from
  that period are not counted in any build figure.
- **782 commits across 156 active days of 189** — a commit on roughly **5 of
  every 6 days**; sustained output, not a weekend prototype.
- **100% solo:** every commit authored by Tom Lang. No other contributors.
- Built in **VS Code** using the **Roo Code** extension — continued on its
  community fork, **Zoo Code**, after the original Roo Code team archived
  the open-source repository (May 15, 2026) to focus on a cloud agent product,
  Roomote ([summary](https://amplifying.ai/coding-agents/roo-code)); the fork kept the desktop IDE extension maintained. Orchestrated **9+ AI agents across 6 LLMs** (Gemini,
  Claude, Grok, ChatGPT, Kimi, GLM). The **12 specialized agent roles** are
  checked into this repo (`.roomodes` + `.roo/rules-pilot-*`).
- Formerly named *aevofab*, renamed to *Pilot for Trades* — same project.

## Scale (measured from the original private repo)
Code, schema and test counts can be re-checked against this snapshot; expect
small deltas from curation.
| Category | Size |
|---|---|
| Application code (AI-written, human-directed) | ~252,000 LOC across ~1,380 files (~100K backend / ~146K frontend / ~5.4K Terraform) |
| Automated tests | ~8,000 tests (~4,950 backend + ~3,070 frontend); ~234,000 test LOC — near 1:1 with app code |
| Database migrations / seeds | 305 Alembic migrations (~390 files incl. seed scripts; ~66,000 LOC), plus categorized seed sets |
| Generated API-contract types | ~55,000 LOC — generated from the OpenAPI spec, not authored |
| Design / architecture / analysis docs | 952 markdown docs in the private original (~680 included in this snapshot) |
| Data model | 193 PostgreSQL tables |
| API surface | 74 route modules; ~700 route operations (~370 production + ~330 env-gated `/test` twins) |

- **Tests** break down as ~4,950 backend test functions (~441 files) and
  ~3,070 frontend test cases — web ~2,350, mobile ~690, marketing 31 (about 690
  more live in the shared `frontend/packages/` and are not in these figures).
  These are source counts of `it`/`test` calls. The last recorded full run
  (2026-10-13) had both frontend suites fully green (2,307 web + 701 mobile tests
  executed; parametrized and skipped cases make run and source counts differ); the backend report notes a small number of known failures, left
  unfixed at hibernation. Coverage that day: 76% backend (line+branch), ~71% web,
  ~75% mobile — see `dev-docs/testing-support/`.
- **API** is fully documented to the OpenAPI standard and browsable/testable via
  interactive Swagger UI in development (disabled in production); the ~700
  operations include about 330 env-gated `/test` twins paired with the secured
  routes.
- **Seed data** is organized by category/scenario (core reference data, platform
  config, QA fixtures, and end-to-end scenarios: quote-to-cash, dispatch,
  mobile-sync, notifications), so the database can be reset and re-populated by
  category for repeatable, isolated testing.

## Integrations (wired, not stubs)
- **Payments — Stripe:** Connect, payment intents, subscriptions. Built and
  exercised end-to-end in test mode, including Connect onboarding; live mode was
  configured and validated (products and prices) but never took a real customer
  payment.
- **Accounting — QuickBooks / Intuit:** two-way sync with conflict diffing.
- **Calendar — Google Calendar:** OAuth 2.0 connection with two-way sync (jobs pushed as
  events; outside events pulled in as technician unavailability).
- **SMS / voice — Telnyx** (production path). An initial **Twilio** integration
  was replaced with Telnyx, which fit this project's 10DLC provisioning needs and
  budget better; remnants remain in the code.
- **Email — SendGrid** (transactional).
- **Auth — AWS Cognito:** user pools + MFA, with a built mobile + web enrollment
  wizard.
- **AWS — boto3:** S3, Lambda.
- **Mobile push — Expo:** built and tested via Expo; the app was never submitted
  to the App Store or Google Play (no store developer accounts) — consistent with
  an R&D build.
- **Offline-first mobile (mid-integration):** an on-device SQLite store and a
  background-sync layer are built and the design is complete, but the subsystem
  was still being integrated at hibernation — finishing the local-DB migrations,
  the foreground sync wiring, and the sync-engine tests is outstanding work.
- **Local AI / voice pipeline — Ollama + Whisper.**
- **Bot protection — Cloudflare Turnstile; maps — Google Maps.**
- **Help-article embeddings — OpenAI** (`text-embedding-3-small`): the one external AI call; it indexes Pilot's own help articles, never customer audio or job data.

## Build & deployment discipline
- **Containerized from day one:** locally, Docker Compose ran Postgres, Redis,
  the Celery worker and beat, Ollama and Whisper, with the API under `uvicorn`.
  In AWS the API, worker and beat ran from the same backend image, with managed
  services (RDS, ElastiCache, a GPU instance) in place of the local containers.
- **One long-lived AWS environment**, built to production spec, served as QA and
  production candidate and was tested after every batch. It never carried
  customer traffic or real user data. A separate QA stack was deployed once,
  tested, and torn down to avoid doubling cost.
- **Infrastructure as code:** all AWS resources defined in Terraform; one
  CloudFront distribution was recreated by hand after an accidental destroy.
  Other manual console changes were limited to testing and setup verification.

> This public snapshot is a **curated subset** of the original private
> repository, sized to demonstrate the method and the engineering — not to be
> run as-is.

**The marketing site is launch-draft copy.** `frontend/apps/marketing/` is
included as source only. It describes the intended product, including features
that were never finished (offline mode, offline voice processing), and contains
pricing, Charter-signup and careers pages written for a launch that never
happened. Testimonials and job listings are labelled placeholders; no testimonial
is from a real customer and no roles are open. Marketing and blog imagery is
AI-generated; no real people or customers are depicted.

## What was changed or removed to publish safely
Nothing was removed silently. Where content was taken out, it's noted here.

**Secrets — replaced with placeholders:** a local dev database password; a
personal ngrok tunnel domain; a Telnyx API key (also deleted in Telnyx); a
SendGrid API key (account closed; secret half never present); QuickBooks
sandbox app credentials and a dev encryption key (sandbox secret rotated).
Infrastructure identifiers (SSH public key, CloudFront domains, Cognito app
client ID, the 10DLC campaign IDs (TCR and Telnyx forms), the Telnyx messaging
profile ID, the platform SMS number, the QuickBooks sandbox company ID, a SendGrid
domain-authentication subdomain, Stripe test-mode meter IDs, fragments of Stripe
price and account IDs, a few development-database record IDs, ACM certificate
validation records, the Google site-verification token, the old Route 53
nameservers, load-balancer rule IDs, and a home-network dev
address) were also replaced with placeholders. Records that are public in DNS
by design (the Cloudflare nameservers and a DKIM public key) are left as
written. An automated key sweep of all
text files, plus a manual review of every image, found no live third-party
credentials or personal endpoints.

**Small changes made for publication:** code comments and docs corrected where they
misdescribed the as-built system; test fixtures and examples moved to
`example.com` email domains and placeholder IDs; the `Jinja2` pin bumped to 3.1.6
(security advisories) and the unused `twilio` dependency removed; the API
favicon pointed at the product's own icon; marketing launch-draft copy, prices
and blog call-to-action links corrected; a few one-off admin scripts made
repo-relative; an unused marketing deploy workflow (which used stored AWS keys)
and unused placeholder images deleted. Application behaviour was not otherwise
changed: the authorization, hardening and
correctness gaps found in a final code read are disclosed in Known Limitations
#27–#30, not fixed. These publication edits were checked by review and by
syntax-parsing every edited file; the test suites were not re-run on this
snapshot. All test, coverage and run figures in this repo come from the private
original.

**Secrets once baked into container images:** during the build, a local `.env`
file was briefly baked into some container images (the prompts and runbooks
record it being found and fixed). The secrets it held were rotated.

**Cognito user pools deleted:** before publication (2026-11-14), both Cognito
user pools (dev and prod) and every test user in them were deleted, so none of
the test accounts or pool endpoints named in the working papers exist any more.

**Working papers left candid on purpose:** the implementation prompts and design
notes show defects being found and fixed, including a "fake" OTP screen and an
MFA mock that were replaced with the real flows, a hollow test that was made
real, and marketing copy that went through drafts (placeholder testimonials,
a switch to a "we" voice). None of that draft copy was ever live as a real
claim; the published marketing source labels its testimonials as placeholders.

**Left as-is on purpose:** the Cloudflare Turnstile *site* key (public by design;
it is served to every browser that loads the form), and the name of the private
source repository (`TomHRMC/pilot`, referenced by the CI/OIDC configuration) —
the GitHub organization is public either way.

**Removed from the snapshot:** vendored Terraform provider/build directories
(large binary bundles); database data dumps (development seed data) — a
schema-only dump (`backend/scripts/schema_dump_20260907_082031.sql`, no rows)
is retained as a schema reference; raw `.eml` captures; mutation-testing
(cosmic-ray) run outputs (the configuration and QA-workflow notes are retained);
a voice-memo audio sample and a Stripe dashboard screenshot; a copy of
Telnyx's 10DLC API specification (vendor document); a superseded
MFA-campaign history note (`telnyx-10dlc-mfa-campaign.md`); a superseded git
commands reference (v1.5) carried over from an earlier project; two superseded early
prompts (`dev-docs/implementation-prompts/archive/`); unused framework-template
logos; and the private
planning and business documents — the launch plan / execution tracker
(`pilot-launch-plan.md`), batch registry, launch-gate docs, agent task logs,
marketing analysis and brand strategy. Many design docs still reference these;
`dev-docs/analysis/Pilot-Delivery-and-Governance.md` summarizes what they held.

**Sanitized (de-identified, functionality unaffected):** real personal email
addresses -> `example.com`; AWS Cognito user-pool IDs -> placeholders; absolute
local paths (`/Users/...`) -> generic paths. Synthetic test addresses in fixtures
and the author's own business domains (`pilotfortrades.com`, `hotrmc.com`) are
left as written. Supplier names in seed data are illustrative; their SKUs and
prices are invented.

**Published clean-room:** assembled by copying chosen files from the private
original, scrubbing them, and initializing a **fresh git history** — so no prior
commit history (and no secret that ever lived in it) is carried over.

## Author & contact
Built by **Tom Lang** — HotRMC (fractional CTO).
Any use beyond the LICENSE: **tom@hotrmc.com**.
