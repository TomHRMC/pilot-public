# Batch MOB-B6 Design — GPS Clock-In + Photo Upload + Structured Messages

**Batch**: MOB-B6 (Mobile — React Native Engineer only)  
**Date**: June 17, 2026  
**Author**: Pilot Architect  
**Status**: DESIGN COMPLETE — Ready for implementation  
**Reference gap analysis**: `dev-docs/analysis/pilot-app-pre-wkstm-3-mvp-ui-api-gap-analysis.md` §2.1, §2.2, §2.3, §2.5, §2.9, §2.10  
**Prerequisites**: B17 Part A complete (adds `GET /api/v1/job-expense-categories`), Tom approval for `expo-location` + `expo-image-picker` native dependencies  
**Approval status**: ✅ Tom has approved `expo-location` and `expo-image-picker` by directing this batch. Proceed with installation.

---

## Overview

MOB-B6 closes 6 P0/P1 mobile gaps that were deferred pending Tom's approval of native dependencies:

1. **GPS Clock-In** — install `expo-location`, capture `checkInLat`/`checkInLng` at clock-in time
2. **Photo Documentation** — install `expo-image-picker`, enable `+ Add Photo` button in `PhotoSection`
3. **Voice Structured Messages** — replace `job_etc_status` and `conflict_summary` stub cards with real rendered components
4. **Expense Categories from API** — replace 5 hardcoded categories with `GET /api/v1/job-expense-categories` (added in B17 Part A)
5. **Manual Sync Trigger** — replace `console.log` in sync screen with actual sync trigger
6. **Voice `types-stub.ts`** — replace local stub type imports with `@pilot/shared-types` imports

No backend changes needed. All required endpoints exist after B17 Part A.

---

## A. Input Read Summary

| Input | What was read | Key finding |
|---|---|---|
| PRD §3.4, §3.15 | GPS clock-in, photo upload, offline sync | GPS required for payroll accuracy + dispute resolution; photos for documentation |
| `features/jobs/components/detail/ClockInOutSection.tsx` | Lines 1–50 | `expo-location` not installed; `TODO` comment with approval note; clock-in handler calls `useCreateTimeEntry.create()` without lat/lng |
| `features/jobs/components/detail/PhotoSection.tsx` | Lines 1–60 | `expo-image-picker` not installed; `+ Add Photo` is a disabled Pressable stub; WatermelonDB `Photo` model exists; upload pipeline code exists |
| `features/voice-quote-creation/components/StructuredMessage.tsx` | Lines 1–80 | `job_etc_status` and `conflict_summary` render raw JSON in stub cards; `quote_preview` is fully implemented as reference |
| `features/jobs/components/detail/ExpenseSection.tsx` | Lines 1–50 | 5 hardcoded categories; `TODO` to replace with API; category dropdown uses local `MVP_EXPENSE_CATEGORIES` array |
| `apps/mobile/package.json` | Full file | **`expo-location` NOT in dependencies**; **`expo-image-picker` NOT in dependencies**; `expo-image` IS installed (for display); `expo-file-system` IS installed (for local file handling) |
| Gap analysis §2.9 | `types-stub.ts` | Voice components import types from local `types-stub.ts` rather than `@pilot/shared-types` |
| Gap analysis §2.10 | Manual sync trigger | `apps/mobile/app/(tabs)/(home)/sync/index.tsx` has `console.log("[SyncPendingScreen] Manual sync triggered")` instead of actual sync call |
| PRD §3.15 | GPS-Verified Check-Ins | `checkInLat`, `checkInLng`, `check_in_gps_variance` captured at clock-in time |
| `backend/api/routes/jobs.py` (from FE-B21 work) | Time entry create endpoint | `JobTimeEntryCreate` schema — verify if it has `check_in_lat`, `check_in_lng` fields (pre-work check needed) |

---

## B. Migration Plan

**No Alembic migrations.** No backend changes.

**Native dependency additions** (install via pnpm in `apps/mobile`):
```bash
cd frontend
pnpm --filter mobile add expo-location expo-image-picker
```

**Pre-work verification** (React Native Engineer runs before coding):
```bash
# Verify expo-location is available for SDK 54
npx expo install expo-location --check

# Verify expo-image-picker is available for SDK 54  
npx expo install expo-image-picker --check

# Check if time entry backend supports lat/lng
grep -n "check_in_lat\|check_in_lng\|checkInLat\|checkInLng" backend/api/schemas/schemas.py | head -10

# Check backend create_time_entry for GPS fields
grep -n "check_in_lat\|check_in_lng" backend/api/routes/jobs.py | head -10

# Find sync orchestrator / SyncProvider to understand manual sync API
grep -rn "SyncOrchestrator\|syncNow\|triggerSync" frontend/apps/mobile/ --include="*.ts" --include="*.tsx" | head -20
```

**Key decision from pre-work**: If `JobTimeEntryCreate` does NOT include `check_in_lat`/`check_in_lng` fields, GPS coordinates are captured and stored in WatermelonDB locally but NOT sent to the backend. The clock-in call proceeds without them. Document this limitation clearly in the code.

---

## C. Execution Order

| # | Task | Files | Dependency |
|---|---|---|---|
| 1 | Install `expo-location` and `expo-image-picker` via pnpm | `package.json` | None |
| 2 | Update `app.json` permissions for location + camera (iOS + Android) | `app.json` | 1 |
| 3 | Replace `types-stub.ts` voice imports with `@pilot/shared-types` | Voice feature files | Run `pnpm sync-api-types` first |
| 4 | Replace hardcoded expense categories with API call | `ExpenseSection.tsx` | B17 confirmed endpoint exists |
| 5 | Add GPS capture to `ClockInOutSection` clock-in flow | `ClockInOutSection.tsx` | 1 |
| 6 | Enable `+ Add Photo` button in `PhotoSection` | `PhotoSection.tsx` | 1 |
| 7 | Replace `job_etc_status` stub with `JobEtcStatusCard` | `StructuredMessage.tsx`, new `JobEtcStatusCard.tsx` | None |
| 8 | Replace `conflict_summary` stub with `ConflictSummaryCard` | `StructuredMessage.tsx`, new `ConflictSummaryCard.tsx` | None |
| 9 | Fix manual sync trigger in sync screen | `app/(tabs)/(home)/sync/index.tsx` | Pre-work: find sync trigger API |
| 10 | Run tests + full verification | — | All above |

---

## D. API Endpoints Consumed

No new endpoints. All existing:

| Component | Endpoint | Notes |
|---|---|---|
| `ExpenseSection` | `GET /api/v1/job-expense-categories` | Added in B17 Part A; replaces hardcoded categories |
| `ClockInOutSection` | `POST /api/v1/jobs/{id}/time-entries` | Existing; add lat/lng if schema supports |
| `PhotoSection` | `POST /api/v1/photos/initiate-upload` + `POST /api/v1/photos/complete-upload` | Already implemented in WatermelonDB offline sync pipeline |

---

## E. Pattern Reuse Decisions

| Pattern | Applied in MOB-B6 |
|---|---|
| Optimistic UI with pending badges | Photo upload uses existing `Photo` WatermelonDB model; shows `uploadProgress` indicator |
| Offline-first | GPS capture is synchronous (fast), so it happens before the clock-in write to WatermelonDB; no offline concern for GPS itself |
| `expo-location` foreground-only | For MVP: request `requestForegroundPermissionsAsync` only (not background). GPS on clock-in only — not continuous tracking. |
| `expo-image-picker` `mediaTypes: 'Images'` | No video capture needed for job photos |

---

## F. Shared Module Interfaces

### F.1 GPS Capture in `ClockInOutSection`

```typescript
// Add to clock-in handler:
import * as Location from 'expo-location';

const handleClockIn = async () => {
  let checkInLat: number | null = null;
  let checkInLng: number | null = null;
  let gpsVariance: number | null = null;

  // Request permission + capture GPS
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status === 'granted') {
    try {
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      checkInLat = loc.coords.latitude;
      checkInLng = loc.coords.longitude;
      gpsVariance = loc.coords.accuracy;  // meters
    } catch (gpsError) {
      // GPS failed — proceed without coordinates (soft failure)
      console.warn('GPS capture failed:', gpsError);
    }
  }
  // Proceed with clock-in regardless of GPS success/failure
  await create({ jobId, userId, startedAt: new Date().toISOString(), checkInLat, checkInLng });
};
```

**Permission request timing**: Request permission on first clock-in attempt. If denied, proceed without GPS (do NOT block clock-in). Show a one-time banner: "Location access helps verify on-site presence" with a dismiss button.

### F.2 Photo Capture in `PhotoSection`

```typescript
import * as ImagePicker from 'expo-image-picker';

const handleAddPhoto = async () => {
  const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  // Also request camera permission for direct capture
  const cameraStatus = await ImagePicker.requestCameraPermissionsAsync();
  
  // Show action sheet: "Take Photo" vs "Choose from Library"
  // iOS: use ActionSheetIOS; Android: custom modal with two options
  
  const result = await ImagePicker.launchCameraAsync({
    // OR: launchImageLibraryAsync
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    quality: 0.8,
    allowsEditing: false,
  });
  
  if (!result.canceled && result.assets[0]) {
    const uri = result.assets[0].uri;
    // Write to WatermelonDB Photo record via existing upload pipeline
    // The existing PhotoSection already has the WatermelonDB write + upload logic
    // Just replace the disabled stub call with this real implementation
  }
};
```

### F.3 `JobEtcStatusCard` Component

```typescript
// features/voice-quote-creation/components/JobEtcStatusCard.tsx
// Props: entity_id (jobId), snapshot_payload
// 
// Live mode (entity_id present): fetch GET /api/v1/jobs/{jobId}/projected-margin
//   Show: Projected Margin %, actual_cost vs quoted_budget
// 
// Snapshot mode (snapshot_payload present): render from frozen data
//   Show: same fields from snapshot_payload
//
// Reference: VoiceQuotePreview as the established pattern for live/snapshot rendering
```

### F.4 `ConflictSummaryCard` Component

```typescript
// features/voice-quote-creation/components/ConflictSummaryCard.tsx
// Props: entity_id (conflictId), snapshot_payload
//
// For MVP: display the snapshot_payload fields in a formatted card
// Fields typically: entity_type, conflict_type, pilot_snapshot, external_snapshot
// Show: "Conflict: [entity_type]" + summary of the two versions
// Link: "Resolve on web →" deep link to web conflict resolution page
// This is simpler than the full resolution UI (which is web-only per PRD)
```

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Does `JobTimeEntryCreate` support `check_in_lat`/`check_in_lng`?** | Verify in pre-work. If yes: pass them. If no: store in WatermelonDB `JobTimeEntry` model locally and document as a future backend sync task. The PRD requires capturing GPS; storage is the important part even if not yet synced. |
| **Should GPS block clock-in if denied?** | No. GPS is additive — it enhances the time entry but must never block a tech from clocking in. Permission denied → proceed without coordinates, no error shown. |
| **Photo capture: camera or library or both?** | Both. Show a simple action: "Take Photo" (camera) and "Choose from Library" (gallery). On iOS use `ActionSheetIOS`; on Android use a simple two-button modal. |
| **`types-stub.ts` replacement — will all types be available after `pnpm sync-api-types`?** | Verify in pre-work. The voice session types (`SessionResponse`, `SessionMessageResponse`) are now in the backend spec since B17 Part A. Run `pnpm sync-api-types` and check which stub types can be replaced. Any that still can't be resolved: keep stub with `// TODO: remove when pnpm sync-api-types delivers this type`. |
| **Manual sync trigger — what's the API?** | Find in pre-work: `grep -rn "SyncOrchestrator\|syncNow\|triggerSync"`. The sync provider should expose a `triggerSync()` or `sync()` function. The sync screen should call it. |
| **Permission requests timing on iOS (pre-OS-prompt screen)?** | The mobile app already handles push notification permission with a pre-explainer screen (per PRD §3.7). For GPS and camera: follow the same pattern — show a one-sentence explainer before the OS prompt fires. |

---

## H. Surface Mockup Reference

**Platform**: Mobile only (`apps/mobile`)

### H.1 Clock-In with GPS

```
┌─────────────────────────────────────────────────────────────┐
│  Clock In                                                   │
│                                                             │
│  📍 Getting location...  (spinner)                         │
│                                                             │
│  → Location captured ✓                                      │
│  OR                                                         │
│  → Clocking in without location (if denied/failed)         │
│                                                             │
│  [Clock In]  (disabled while capturing)                     │
└─────────────────────────────────────────────────────────────┘
```

### H.2 Photo Section (enabled)

```
┌─────────────────────────────────────────────────────────────┐
│  Photos                              [+ Add Photo]          │
│  ─────────────────────────────────────────────────────────  │
│  [📷]         [📷]         [📷]                            │
│  Uploading... Synced       Synced                           │
└─────────────────────────────────────────────────────────────┘
```

### H.3 Voice `job_etc_status` Card (enabled)

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Job Status — Johnson Panel Upgrade                      │
│  Actual Cost: $360 / Budget: $480                           │
│  Projected Margin: 24.5%  ✅ On track                       │
│  Hours Remaining (ETC): 2.5h                                │
└─────────────────────────────────────────────────────────────┘
```

---

## I. Component Manifest

| Component | Path | New or Modify | Notes |
|---|---|---|---|
| `ClockInOutSection` | `features/jobs/components/detail/ClockInOutSection.tsx` | **Modify** | Add GPS capture; permission request; soft failure if denied |
| `PhotoSection` | `features/jobs/components/detail/PhotoSection.tsx` | **Modify** | Enable `+ Add Photo`; `expo-image-picker` capture; camera + library options |
| `JobEtcStatusCard` | `features/voice-quote-creation/components/JobEtcStatusCard.tsx` | **New** | Live/snapshot job profitability card |
| `ConflictSummaryCard` | `features/voice-quote-creation/components/ConflictSummaryCard.tsx` | **New** | Conflict summary with "Resolve on web" link |
| `StructuredMessage` | `features/voice-quote-creation/components/StructuredMessage.tsx` | **Modify** | Replace job_etc_status + conflict_summary stubs |
| `ExpenseSection` | `features/jobs/components/detail/ExpenseSection.tsx` | **Modify** | Replace hardcoded categories with `GET /api/v1/job-expense-categories` |
| `sync/index.tsx` | `app/(tabs)/(home)/sync/index.tsx` | **Modify** | Replace `console.log` with actual sync trigger |
| `types-stub.ts` | `features/voice-quote-creation/types-stub.ts` | **Modify/Delete** | Replace resolvable imports with `@pilot/shared-types`; keep stubs for types not yet in spec |
| `package.json` | `apps/mobile/package.json` | **Modify** | Add `expo-location`, `expo-image-picker` |
| `app.json` | `apps/mobile/app.json` | **Modify** | Add location + camera permissions |
