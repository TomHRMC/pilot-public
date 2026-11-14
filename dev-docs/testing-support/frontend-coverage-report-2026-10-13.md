# Frontend Test Coverage Report — Pilot for Trades

**Date:** 2026-10-13
**Commands:** `vitest --coverage` (web) · `jest --coverage` (mobile)

## Web (vitest) — `frontend/apps/web`

| Metric | Coverage |
|---|---:|
| Statements | 70.64% |
| Branches | 75.61% |
| Functions | 61.24% |
| Lines | 70.64% |

**Tests:** 2,307 passed across 373 test files — **all passing (0 failing)**.
Full HTML report: `frontend/apps/web/coverage/index.html` · raw log: `frontend/coverage-web.log`.

## Mobile (jest) — `frontend/apps/mobile`

| Metric | Coverage |
|---|---:|
| Statements | 74.31% |
| Branches | 65.90% |
| Functions | 65.70% |
| Lines | 75.37% |

**Tests:** 701 passed across 116 suites — **all passing (0 failing)**.
Full HTML report: `frontend/apps/mobile/coverage/lcov-report/index.html` · raw log: `frontend/coverage-mobile.log`.

## Full-stack context

Measured coverage across all three independently-tooled codebases sits in a tight, consistent band:

| Tier | Coverage | Tests |
|---|---:|---|
| Backend (pytest) | 76% line+branch · 79.1% statement | ~4,900+ (few known-failing in snapshot) |
| Web (vitest) | ~70.6% lines | 2,307 — all passing |
| Mobile (jest) | ~75.4% lines | 701 — all passing |

The uniform ~71–76% profile across three separate stacks reflects a deliberate, consistent testing standard rather than uneven effort. See `backend-coverage-report-2026-10-13.md` for the backend breakdown by layer.
