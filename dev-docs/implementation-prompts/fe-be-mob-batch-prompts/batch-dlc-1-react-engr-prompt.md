# Implementation Prompt: DLC-1 — 10DLC Compliance Engineering (Frontend)

**Mode**: Pilot React Engineer  
**Batch**: DLC-1  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §P1 — 10DLC Compliance Engineering  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-dlc-1-design.md`  
**Estimated session**: 2–3 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: DLC-1 Python Engineer — **must complete first**. Run `pnpm sync-api-types` as your first Pre-Work step.

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-dlc-1-design.md`** — every section (A–G)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing ANY hook or API call, verify the endpoint exists in `backend/openapi_schema_map.md`. If it is NOT there → **STOP and ask Tom**.
- **Rule 1.2**: Do NOT invent URL patterns or parameter names. Every shape comes from `openapi.json` or the design doc.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — all TypeScript types for backend payloads come from `@pilot/shared-types`.
- **Rule 2**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned for `/api/v1/...` calls.
- **Rule 7**: Check `packages/ui/src/index.ts` before creating any new component — `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>`, `<SettingControl>` are all available.
- **Rule 8**: No new npm dependencies without first checking what is already installed in `package.json`.
- **Rule 9**: Route files in `apps/web/src/app/(authed)/` MUST be thin server components — no `"use client"`, no data fetching. One line: `return <FeatureComponent />;`
- **Rule 10**: If ANY test fails during your work — even pre-existing — **fix it before declaring the batch done**.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these decisions are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Does the API reject missing attestation checkbox? | **No** — API accepts customers without attestation | Frontend enforces the block; API is not a gatekeeper. Backend only triggers opt-in flow if `sms_attestation_checked=True` |
| Where does 10DLC profile form live? | `/settings` page — new section matching `email-branding` pattern | Same RBAC (`settings.manage`), same single-row upsert |
| New `PermissionKey` required? | **No** — reuses `settings.view` and `settings.manage` | These keys already exist in `permissions.ts` |
| Does attestation checkbox appear on both create AND edit customer? | **Yes** — on `CustomerForm.tsx` shared component | Both `CreateCustomerModal` and `CustomerOverviewTab` use `CustomerForm` |
| Is `sms_consent_ip_address` captured client-side? | **Yes** — use a `/api/v1/auth/me` or similar if available; if not, omit and let backend default to `"unknown"` | EIN best-effort; backend already defaults to `"unknown"` |

---

## Pre-Work: Establish Regression Baseline

Before touching any file:

```bash
cd <repo>/frontend

# Web tests:
pnpm --filter web test 2>&1 | tail -5

# Shared UI (if you touch packages/ui):
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Record the exact counts. These must still pass at the end of the batch.

> **If any tests are already failing**: Do NOT proceed. Confirm with Tom or fix before starting.

---

## Pre-Work: Sync API Types

**This is your first action after reading the required files.**

```bash
cd <repo>/frontend
pnpm sync-api-types
```

This regenerates `packages/shared-types/src/api-schema.d.ts` from the backend OpenAPI spec the Python Engineer updated. All new backend payload types come from `@pilot/shared-types`.

> **If `pnpm sync-api-types` fails** because the backend hasn't run `python export_openapi_json.py` yet → STOP. Do not start implementation until the Python Engineer batch is complete and types are synced.

---

## Pre-Work: Verify Endpoints

Verify these endpoints exist before writing any hook:

```bash
grep -A 5 "10dlc-profile" backend/openapi_schema_map.md
grep -A 3 "sms_attestation_checked\|sms_consent_ip_address" backend/openapi_schema_map.md
```

**Expected endpoints for this batch:**

| Hook | Endpoint | Must Exist In |
|---|---|---|
| `use10DlcProfile` | `GET /api/v1/settings/10dlc-profile` | `openapi_schema_map.md` |
| `useUpdate10DlcProfile` | `PUT /api/v1/settings/10dlc-profile` | `openapi_schema_map.md` |
| `useCreateCustomer` (existing — modified) | `POST /api/v1/customers/` | Already exists |
| `useUpdateCustomer` (existing — modified) | `PATCH /api/v1/customers/{id}` | Already exists |

> **If `GET /api/v1/settings/10dlc-profile` is NOT in `openapi_schema_map.md` → STOP. Do not invent a URL. Ask Tom.**

---

## Pre-Work: Read These Source Files

Read each of these with `read_file` before writing any code:

```
frontend/apps/web/src/features/customers/components/CustomerForm.tsx
  ← Why: This is the shared form for create + edit; you will add the attestation checkbox here.
    Read the full CustomerFormValues interface and props before adding any field.

frontend/apps/web/src/features/customers/components/CustomerOverviewTab.tsx
  ← Why: Understand how CustomerForm is used in edit mode and what values it passes to useUpdateCustomer.

frontend/apps/web/src/features/customers/components/CreateCustomerModal.tsx
  ← Why: Understand how CustomerForm is used in create mode and what values it passes to useCreateCustomer.

frontend/apps/web/src/features/customers/hooks/useCreateCustomer.ts
  ← Why: Understand what payload shape is sent to POST /api/v1/customers/.

frontend/apps/web/src/features/customers/hooks/useUpdateCustomer.ts
  ← Why: Understand what payload shape is sent to PATCH /api/v1/customers/{id}.

frontend/apps/web/src/features/email-branding/
  ← Why: Pattern reference for a single-row-per-tenant settings form with GET/PUT.
    Read the feature folder structure, hooks, and component to understand the pattern.

frontend/apps/web/src/mocks/handlers/index.ts
  ← Why: Understand how to register new MSW handler files in the barrel export.

frontend/packages/ui/src/index.ts
  ← Why: Confirm available shared components before creating new ones.
```

Also run:
```bash
# Find the email-branding feature folder (confirm path)
find frontend/apps/web/src/features/email-branding -name "*.ts" -o -name "*.tsx" | sort

# Find existing settings hooks/components
find frontend/apps/web/src/features/settings -name "*.ts" -o -name "*.tsx" | sort | head -20

# Confirm MSW handler files
find frontend/apps/web/src/mocks/handlers -name "*.ts" | sort

# Confirm shared component availability
grep -n "LoadingState\|ErrorState\|SettingControl\|RoleGate" frontend/packages/ui/src/index.ts | head -20
```

---

## Context: What This Batch Does

| Step | File(s) | What |
|---|---|---|
| STEP 1 | `CustomerForm.tsx` | Add attestation checkbox + `CustomerFormValues` field |
| STEP 2 | `useCreateCustomer.ts` + `useUpdateCustomer.ts` | Pass `sms_attestation_checked` in payload |
| STEP 3 | New `features/sms-compliance/` or inline in `features/settings/` | `use10DlcProfile` hook + `useUpdate10DlcProfile` mutation |
| STEP 4 | New `TenantDlcProfileForm.tsx` | 10DLC profile form component (RBAC: settings.manage) |
| STEP 5 | Settings page wiring | Wire form into settings surface |
| STEP 6 | MSW handlers | Add handlers for the two new endpoints |
| STEP 7 | Tests | Unit + integration tests |

---

## STEP 1 — Add Attestation Checkbox to `CustomerForm.tsx`

**Read the file first. Adjust all examples to match what you actually find.**

File: `frontend/apps/web/src/features/customers/components/CustomerForm.tsx`

### 1-A: Extend `CustomerFormValues` interface

Add to the `CustomerFormValues` interface:

```typescript
// Add to CustomerFormValues:
sms_attestation_checked?: boolean;   // defaults to false
sms_consent_ip_address?: string;     // not shown in UI; passed through if available
```

### 1-B: Add checkbox state

Inside `CustomerForm`, add state:

```typescript
const [smsAttestationChecked, setSmsAttestationChecked] = useState(
  initialValues?.sms_attestation_checked ?? false,
);
```

### 1-C: Add checkbox UI below the `mobile_phone` field

Add this block immediately after the mobile phone `<div>` block and before the form action buttons. Only show it when `mobile_phone` has a non-empty value:

```tsx
{/* DLC-1: SMS Offline Consent Attestation — required when phone is entered */}
{mobilePhone.trim() && (
  <div className="mb-6 p-4 border border-neutral-200 rounded-md bg-neutral-50">
    <label className="flex items-start gap-3 cursor-pointer">
      <input
        type="checkbox"
        id="sms-attestation-checkbox"
        checked={smsAttestationChecked}
        onChange={(e) => setSmsAttestationChecked(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-500"
        data-testid="sms-attestation-checkbox"
      />
      <span className="text-sm text-neutral-700 leading-relaxed">
        I confirm that I have received explicit, documented consent from this
        customer to send them SMS notifications regarding their service. I
        understand that sending unsolicited messages violates platform policy and
        federal law.
      </span>
    </label>
    {mobilePhone.trim() && !smsAttestationChecked && (
      <p
        className="mt-2 text-xs text-alert-600"
        data-testid="sms-attestation-warning"
        role="alert"
      >
        ⚠ You must confirm consent before saving a mobile phone number.
      </p>
    )}
  </div>
)}
```

### 1-D: Block submit when phone is present but checkbox unchecked

The submit button must be disabled when `mobilePhone.trim()` is non-empty AND `smsAttestationChecked` is false.

Read the current submit button disabled logic before modifying it. Add to the existing `disabled` condition:

```typescript
// Existing disabled logic (read the file — this is approximate):
const isSubmitDisabled =
  isSubmitting ||
  !displayName.trim() ||
  // DLC-1: block if phone present without attestation
  (mobilePhone.trim() !== "" && !smsAttestationChecked);
```

### 1-E: Include in `onSubmit()` call

When calling `onSubmit(values)`, include the new fields:

```typescript
onSubmit({
  // ... existing fields
  sms_attestation_checked: smsAttestationChecked,
  // sms_consent_ip_address: omit here — not captured client-side in this MVP
});
```

> **Read the current `onSubmit` call in the file before modifying.** Add only the new field — do not remove existing fields.

---

## STEP 2 — Pass Attestation in Customer Hooks

### 2-A: `useCreateCustomer.ts`

**Read the file first.** The hook POSTs to `POST /api/v1/customers/`. After reading, extend the payload to include `sms_attestation_checked` when it's `true`:

```typescript
// In the mutationFn — read the current payload shape first, then add:
sms_attestation_checked: values.sms_attestation_checked ?? false,
// Omit sms_consent_ip_address — backend defaults to "unknown"
```

### 2-B: `useUpdateCustomer.ts`

**Read the file first.** The hook PATCHes to `PATCH /api/v1/customers/{id}`. Add the same field to the payload:

```typescript
sms_attestation_checked: values.sms_attestation_checked ?? false,
```

> **Only add `sms_attestation_checked` to the payload.** Do not restructure the existing payload. Do not add `sms_consent_ip_address` unless you can capture it reliably — it defaults to `"unknown"` in the backend.

---

## STEP 3 — New Hooks: `use10DlcProfile` and `useUpdate10DlcProfile`

Create a new feature folder: `frontend/apps/web/src/features/sms-compliance/` (or place within `settings/` if that's where the pattern lives — read the `email-branding` feature folder structure first to match the established pattern).

### Hook file: `hooks/use10DlcProfile.ts`

```typescript
"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

// Adjust type to match what pnpm sync-api-types delivers
export interface Tenant10DlcProfileData {
  tenant_id: string;
  legal_business_name: string | null;
  dba_name: string | null;
  ein_masked: string | null;
  hq_address_line1: string | null;
  hq_address_line2: string | null;
  hq_city: string | null;
  hq_state: string | null;
  hq_postal_code: string | null;
  hq_country: string;
  support_email: string | null;
  support_phone: string | null;
  updated_at: string | null;
}

export const DLC_PROFILE_QUERY_KEY = ["settings", "10dlc-profile"] as const;

export function use10DlcProfile() {
  return useQuery<Tenant10DlcProfileData | null>({
    queryKey: DLC_PROFILE_QUERY_KEY,
    queryFn: async () => {
      try {
        const res = await apiClient.get<Tenant10DlcProfileData>(
          "/api/v1/settings/10dlc-profile",
        );
        return res.data;
      } catch (err: unknown) {
        // 404 means not yet configured — return null instead of throwing
        if (
          typeof err === "object" &&
          err !== null &&
          "response" in err &&
          (err as { response: { status: number } }).response?.status === 404
        ) {
          return null;
        }
        throw err;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
}
```

### Hook file: `hooks/useUpdate10DlcProfile.ts`

```typescript
"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import { DLC_PROFILE_QUERY_KEY } from "./use10DlcProfile";
import type { Tenant10DlcProfileData } from "./use10DlcProfile";

export interface Update10DlcProfilePayload {
  legal_business_name: string;
  dba_name?: string | null;
  ein?: string | null;
  hq_address_line1?: string | null;
  hq_address_line2?: string | null;
  hq_city?: string | null;
  hq_state?: string | null;
  hq_postal_code?: string | null;
  hq_country?: string;
  support_email?: string | null;
  support_phone?: string | null;
}

export function useUpdate10DlcProfile() {
  const queryClient = useQueryClient();

  return useMutation<Tenant10DlcProfileData, unknown, Update10DlcProfilePayload>(
    {
      mutationFn: async (payload) => {
        const res = await apiClient.put<Tenant10DlcProfileData>(
          "/api/v1/settings/10dlc-profile",
          payload,
        );
        return res.data;
      },
      onSuccess: () => {
        void queryClient.invalidateQueries({ queryKey: DLC_PROFILE_QUERY_KEY });
      },
    },
  );
}
```

> **Read the established hook pattern in `email-branding` hooks before finalizing.** Adjust imports and query key structure to match what you find.

---

## STEP 4 — New Component: `TenantDlcProfileForm.tsx`

**Read the email-branding feature component first** to understand the established single-row-per-tenant settings form pattern. Match it structurally.

File: `frontend/apps/web/src/features/sms-compliance/components/TenantDlcProfileForm.tsx` (or matching location to `email-branding`)

```tsx
"use client";

/**
 * TenantDlcProfileForm — 10DLC business registration profile form.
 *
 * DLC-1: Used in /settings page under "SMS & 10DLC" section.
 * RBAC: settings.manage (PUT). settings.view (GET — read-only display).
 *
 * This data is required to provision Telnyx sub-brand per tenant
 * for SMS campaign registration (carrier TCR submission by Tom).
 */

import { useState, useEffect } from "react";
import { RoleGate } from "@pilot/ui/role-gate";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { use10DlcProfile } from "../hooks/use10DlcProfile";
import { useUpdate10DlcProfile } from "../hooks/useUpdate10DlcProfile";

const LABEL_CLASS = "block text-sm font-medium text-neutral-700 mb-1";
const INPUT_CLASS =
  "w-full border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent";

export function TenantDlcProfileForm() {
  const { data: profile, isLoading, isError } = use10DlcProfile();
  const updateProfile = useUpdate10DlcProfile();

  // Form state
  const [legalBusinessName, setLegalBusinessName] = useState("");
  const [dbaName, setDbaName] = useState("");
  const [ein, setEin] = useState("");
  const [addressLine1, setAddressLine1] = useState("");
  const [addressLine2, setAddressLine2] = useState("");
  const [city, setCity] = useState("");
  const [stateCode, setStateCode] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [supportEmail, setSupportEmail] = useState("");
  const [supportPhone, setSupportPhone] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Populate form from loaded profile
  useEffect(() => {
    if (profile) {
      setLegalBusinessName(profile.legal_business_name ?? "");
      setDbaName(profile.dba_name ?? "");
      // EIN is masked on read — do not pre-populate (user re-enters to update)
      setAddressLine1(profile.hq_address_line1 ?? "");
      setAddressLine2(profile.hq_address_line2 ?? "");
      setCity(profile.hq_city ?? "");
      setStateCode(profile.hq_state ?? "");
      setPostalCode(profile.hq_postal_code ?? "");
      setSupportEmail(profile.support_email ?? "");
      setSupportPhone(profile.support_phone ?? "");
    }
  }, [profile]);

  if (isLoading) {
    return <LoadingState type="inline" label="Loading 10DLC profile..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load 10DLC profile"
        description="Check your connection and try again."
      />
    );
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaveError(null);
    setSaveSuccess(false);

    if (!legalBusinessName.trim()) {
      setSaveError("Legal Business Name is required.");
      return;
    }

    try {
      await updateProfile.mutateAsync({
        legal_business_name: legalBusinessName.trim(),
        dba_name: dbaName.trim() || null,
        ein: ein.trim() || undefined,   // only send if user typed something
        hq_address_line1: addressLine1.trim() || null,
        hq_address_line2: addressLine2.trim() || null,
        hq_city: city.trim() || null,
        hq_state: stateCode.trim().toUpperCase() || null,
        hq_postal_code: postalCode.trim() || null,
        support_email: supportEmail.trim() || null,
        support_phone: supportPhone.trim() || null,
      });
      setSaveSuccess(true);
    } catch {
      setSaveError("Failed to save profile. Please try again.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-base font-semibold text-neutral-900">
          SMS Business Profile (10DLC)
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Required for carrier registration. This data is used to provision your
          dedicated SMS number under TCR compliance.
        </p>
        {profile?.ein_masked && (
          <p className="text-xs text-neutral-400 mt-1">
            Current EIN on file: <span className="font-mono">{profile.ein_masked}</span>.
            Enter a new value below to update.
          </p>
        )}
      </div>

      <RoleGate permission="settings.manage">
        <form onSubmit={(e) => void handleSave(e)} className="space-y-4" data-testid="dlc-profile-form">
          {/* Legal Business Name */}
          <div>
            <label htmlFor="dlc-legal-name" className={LABEL_CLASS}>
              Legal Business Name <span className="text-alert-600">*</span>
            </label>
            <input
              id="dlc-legal-name"
              type="text"
              value={legalBusinessName}
              onChange={(e) => setLegalBusinessName(e.target.value)}
              placeholder="Example Holdings, LLC"
              className={INPUT_CLASS}
              data-testid="dlc-legal-name-input"
            />
          </div>

          {/* DBA Name */}
          <div>
            <label htmlFor="dlc-dba-name" className={LABEL_CLASS}>
              DBA Name <span className="text-neutral-400">(optional)</span>
            </label>
            <input
              id="dlc-dba-name"
              type="text"
              value={dbaName}
              onChange={(e) => setDbaName(e.target.value)}
              placeholder="Pilot for Trades"
              className={INPUT_CLASS}
              data-testid="dlc-dba-name-input"
            />
          </div>

          {/* EIN */}
          <div>
            <label htmlFor="dlc-ein" className={LABEL_CLASS}>
              EIN / Tax ID <span className="text-neutral-400">(optional)</span>
            </label>
            <input
              id="dlc-ein"
              type="text"
              value={ein}
              onChange={(e) => setEin(e.target.value)}
              placeholder="12-3456789 (leave blank to keep existing)"
              className={INPUT_CLASS}
              data-testid="dlc-ein-input"
            />
          </div>

          {/* HQ Address */}
          <fieldset className="space-y-3 border border-neutral-100 rounded-md p-4">
            <legend className="text-sm font-medium text-neutral-700 px-1">
              HQ Address
            </legend>
            <div>
              <label htmlFor="dlc-address-line1" className={LABEL_CLASS}>
                Address Line 1
              </label>
              <input
                id="dlc-address-line1"
                type="text"
                value={addressLine1}
                onChange={(e) => setAddressLine1(e.target.value)}
                placeholder="123 Main Street"
                className={INPUT_CLASS}
                data-testid="dlc-address-line1-input"
              />
            </div>
            <div>
              <label htmlFor="dlc-address-line2" className={LABEL_CLASS}>
                Address Line 2 <span className="text-neutral-400">(optional)</span>
              </label>
              <input
                id="dlc-address-line2"
                type="text"
                value={addressLine2}
                onChange={(e) => setAddressLine2(e.target.value)}
                placeholder="Suite 100"
                className={INPUT_CLASS}
              />
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <div className="col-span-2 sm:col-span-1">
                <label htmlFor="dlc-city" className={LABEL_CLASS}>
                  City
                </label>
                <input
                  id="dlc-city"
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="Denver"
                  className={INPUT_CLASS}
                  data-testid="dlc-city-input"
                />
              </div>
              <div>
                <label htmlFor="dlc-state" className={LABEL_CLASS}>
                  State
                </label>
                <input
                  id="dlc-state"
                  type="text"
                  value={stateCode}
                  onChange={(e) => setStateCode(e.target.value.toUpperCase())}
                  placeholder="CO"
                  maxLength={2}
                  className={INPUT_CLASS}
                  data-testid="dlc-state-input"
                />
              </div>
              <div>
                <label htmlFor="dlc-postal" className={LABEL_CLASS}>
                  ZIP
                </label>
                <input
                  id="dlc-postal"
                  type="text"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  placeholder="80202"
                  className={INPUT_CLASS}
                  data-testid="dlc-postal-input"
                />
              </div>
            </div>
          </fieldset>

          {/* Support Contact */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="dlc-support-email" className={LABEL_CLASS}>
                Support Email
              </label>
              <input
                id="dlc-support-email"
                type="email"
                value={supportEmail}
                onChange={(e) => setSupportEmail(e.target.value)}
                placeholder="support@pilotfortrades.com"
                className={INPUT_CLASS}
                data-testid="dlc-support-email-input"
              />
            </div>
            <div>
              <label htmlFor="dlc-support-phone" className={LABEL_CLASS}>
                Support Phone
              </label>
              <input
                id="dlc-support-phone"
                type="tel"
                value={supportPhone}
                onChange={(e) => setSupportPhone(e.target.value)}
                placeholder="+13035550000"
                className={INPUT_CLASS}
                data-testid="dlc-support-phone-input"
              />
            </div>
          </div>

          {/* Feedback */}
          {saveSuccess && (
            <p className="text-sm text-success-700 bg-success-50 border border-success-200 rounded px-3 py-2" data-testid="dlc-save-success">
              ✓ 10DLC profile saved successfully.
            </p>
          )}
          {saveError && (
            <p className="text-sm text-alert-700 bg-alert-50 border border-alert-200 rounded px-3 py-2" role="alert" data-testid="dlc-save-error">
              {saveError}
            </p>
          )}

          {/* Submit */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={updateProfile.isPending || !legalBusinessName.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
              data-testid="dlc-save-btn"
            >
              {updateProfile.isPending ? "Saving…" : "Save Profile"}
            </button>
          </div>
        </form>
      </RoleGate>
    </div>
  );
}
```

---

## STEP 5 — Wire `TenantDlcProfileForm` into the Settings Surface

**Read the settings feature files first** to understand how existing settings sections (like email branding) are wired.

```bash
find frontend/apps/web/src/features/settings -name "*.tsx" -o -name "*.ts" | sort
find frontend/apps/web/src/app -path "*settings*" -name "*.tsx" | sort | head -20
```

Find the settings page that contains the email branding section. Add a new "SMS & 10DLC" section after the email branding section:

```tsx
import { TenantDlcProfileForm } from "@/features/sms-compliance/components/TenantDlcProfileForm";
// (adjust import path to match actual location)

// In the settings page, after the email branding section:
<section>
  <TenantDlcProfileForm />
</section>
```

> **Do not create a new settings page.** Find where `email-branding` or `TenantEmailBranding` content is rendered in the settings surface and add the 10DLC form in the same section below it.

---

## STEP 6 — MSW Handlers

Create: `frontend/apps/web/src/mocks/handlers/dlcHandlers.ts`

```typescript
import { http, HttpResponse } from "msw";

const MOCK_DLC_PROFILE = {
  tenant_id: "t-test-001",
  legal_business_name: "Smith Electrical LLC",
  dba_name: null,
  ein_masked: "**-***1234",
  hq_address_line1: "123 Main Street",
  hq_address_line2: null,
  hq_city: "Denver",
  hq_state: "CO",
  hq_postal_code: "80202",
  hq_country: "US",
  support_email: "support@smithelectrical.example.com",
  support_phone: "+13035550000",
  updated_at: "2026-07-05T18:00:00Z",
};

export const dlcHandlers = [
  http.get("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json(MOCK_DLC_PROFILE),
  ),

  http.put("/api/v1/settings/10dlc-profile", async ({ request }) => {
    const body = (await request.json()) as typeof MOCK_DLC_PROFILE;
    return HttpResponse.json({
      ...MOCK_DLC_PROFILE,
      ...body,
      ein_masked: body.ein ? "**-***" + body.ein.slice(-4) : MOCK_DLC_PROFILE.ein_masked,
    });
  }),
];
```

**Register in barrel `index.ts`:**

```typescript
// frontend/apps/web/src/mocks/handlers/index.ts
import { dlcHandlers } from "./dlcHandlers";

export const handlers = [
  ...existingHandlers,
  ...dlcHandlers, // ← ADD THIS
];
```

> **Read the current `index.ts` before modifying.** Do not create a duplicate handler for a path that already has one. Add `...dlcHandlers` at the end.

---

## STEP 7 — Tests

### 7-A: Unit test — `TenantDlcProfileForm`

File: `frontend/apps/web/src/features/sms-compliance/components/__tests__/TenantDlcProfileForm.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll, afterEach, afterAll } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";
import { TenantDlcProfileForm } from "../TenantDlcProfileForm";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";

vi.mock("next/navigation", () => ({ usePathname: () => "/settings" }));

const MOCK_PROFILE = {
  tenant_id: "t-001",
  legal_business_name: "Smith Electrical LLC",
  dba_name: null,
  ein_masked: "**-***1234",
  hq_address_line1: null,
  hq_address_line2: null,
  hq_city: null,
  hq_state: null,
  hq_postal_code: null,
  hq_country: "US",
  support_email: null,
  support_phone: null,
  updated_at: null,
};

const server = setupServer(
  http.get("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json(MOCK_PROFILE),
  ),
  http.put("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json({ ...MOCK_PROFILE, legal_business_name: "Updated LLC" }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthValue(role = "owner"): AuthContextValue {
  return {
    user: { id: "u1", email: "owner@example.com", role, tenantId: "t-001", displayName: "Owner", accessToken: "tok" },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function createWrapper(role = "owner") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("TenantDlcProfileForm", () => {
  it("renders without crashing", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId("dlc-profile-form")).toBeTruthy();
    });
  });

  it("pre-populates form with loaded profile data", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      const input = screen.getByTestId("dlc-legal-name-input") as HTMLInputElement;
      expect(input.value).toBe("Smith Electrical LLC");
    });
  });

  it("shows masked EIN from profile", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText(/\*\*-\*\*\*1234/)).toBeTruthy();
    });
  });

  it("save button is disabled when legal_business_name is empty", async () => {
    server.use(
      http.get("/api/v1/settings/10dlc-profile", () => HttpResponse.json({ ...MOCK_PROFILE, legal_business_name: "" })),
    );
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => {
      const btn = screen.getByTestId("dlc-save-btn") as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
    });
  });

  it("shows success message after successful save", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId("dlc-profile-form"));

    fireEvent.submit(screen.getByTestId("dlc-profile-form"));
    await waitFor(() => {
      expect(screen.getByTestId("dlc-save-success")).toBeTruthy();
    });
  });

  it("shows error message when save fails", async () => {
    server.use(
      http.put("/api/v1/settings/10dlc-profile", () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );
    render(<TenantDlcProfileForm />, { wrapper: createWrapper() });
    await waitFor(() => screen.getByTestId("dlc-profile-form"));

    fireEvent.submit(screen.getByTestId("dlc-profile-form"));
    await waitFor(() => {
      expect(screen.getByTestId("dlc-save-error")).toBeTruthy();
    });
  });

  it("form is NOT rendered for tech role (settings.manage required)", async () => {
    render(<TenantDlcProfileForm />, { wrapper: createWrapper("tech") });
    await waitFor(() => {
      expect(screen.queryByTestId("dlc-profile-form")).toBeNull();
    });
  });
});
```

### 7-B: Unit test — `CustomerForm` attestation checkbox

File: `frontend/apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx`

**Read the existing test file first.** Add new tests — do NOT remove existing tests:

```typescript
// ADD to the existing CustomerForm test describe block:

it("attestation checkbox does NOT appear when mobile_phone is empty", () => {
  render(<CustomerForm {...defaultProps} />);
  // mobile_phone is empty by default → checkbox should not render
  expect(screen.queryByTestId("sms-attestation-checkbox")).toBeNull();
});

it("attestation checkbox appears when mobile_phone has a value", async () => {
  render(<CustomerForm {...defaultProps} />);
  // Type a phone number
  fireEvent.change(screen.getByLabelText(/mobile phone/i), {
    target: { value: "+13035550001" },
  });
  await waitFor(() => {
    expect(screen.getByTestId("sms-attestation-checkbox")).toBeTruthy();
  });
});

it("submit is blocked when phone present but attestation unchecked", async () => {
  render(<CustomerForm {...defaultProps} />);
  fireEvent.change(screen.getByLabelText(/display name/i), {
    target: { value: "Smith Electric" },
  });
  fireEvent.change(screen.getByLabelText(/mobile phone/i), {
    target: { value: "+13035550001" },
  });
  // Checkbox is unchecked by default
  await waitFor(() => {
    const submit = screen.getByTestId("customer-form-submit") as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });
});

it("submit is enabled when phone present AND attestation checked", async () => {
  render(<CustomerForm {...defaultProps} />);
  fireEvent.change(screen.getByLabelText(/display name/i), {
    target: { value: "Smith Electric" },
  });
  fireEvent.change(screen.getByLabelText(/mobile phone/i), {
    target: { value: "+13035550001" },
  });
  await waitFor(() => screen.getByTestId("sms-attestation-checkbox"));
  fireEvent.click(screen.getByTestId("sms-attestation-checkbox"));

  const submit = screen.getByTestId("customer-form-submit") as HTMLButtonElement;
  expect(submit.disabled).toBe(false);
});

it("onSubmit includes sms_attestation_checked=true when checkbox checked", async () => {
  const onSubmit = vi.fn();
  render(<CustomerForm {...defaultProps} onSubmit={onSubmit} />);
  fireEvent.change(screen.getByLabelText(/display name/i), { target: { value: "Smith" } });
  fireEvent.change(screen.getByLabelText(/mobile phone/i), { target: { value: "+13035550001" } });
  await waitFor(() => screen.getByTestId("sms-attestation-checkbox"));
  fireEvent.click(screen.getByTestId("sms-attestation-checkbox"));
  fireEvent.click(screen.getByTestId("customer-form-submit"));

  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({ sms_attestation_checked: true }),
  );
});
```

> **Add these tests to the existing describe block.** Read the existing file first to find the correct describe block and import pattern. Do not duplicate imports.

### 7-C: Integration test

File: `frontend/apps/web/src/__tests__/batch_dlc_1/dlc-profile.integration.test.tsx`

Minimum coverage:
1. Settings page renders `TenantDlcProfileForm` without crashing
2. RBAC: owner sees the form; tech does not
3. Form pre-populates from MSW mock data
4. Successful PUT fires the correct endpoint

---

## Final Verification

### Phase 1 — Targeted tests (run after each task group)

```bash
cd <repo>/frontend

# After CustomerForm changes:
npx vitest run apps/web/src/features/customers/components/__tests__/CustomerForm.test.tsx 2>&1 | tail -10

# After TenantDlcProfileForm:
npx vitest run apps/web/src/features/sms-compliance/components/__tests__/TenantDlcProfileForm.test.tsx 2>&1 | tail -10

# Run all web tests:
pnpm --filter web test 2>&1 | tail -6
```

Fix any failure before moving to the next task.

### Phase 2 — Full verification (run once at the very end)

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== DLC-1 REACT FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — DLC-1 React

Update `dev-docs/analysis/pilot-launch-plan.md` §DLC-1 when each item is done:

- [ ] Pre-modification regression baseline captured (zero pre-existing failures, or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — no new type errors
- [ ] Design doc fully read before writing any code (all sections A–G)
- [ ] All mandatory source files read before modifying (`CustomerForm.tsx`, `email-branding` feature, `mocks/handlers/index.ts`, `packages/ui/src/index.ts`)
- [ ] `GET /api/v1/settings/10dlc-profile` verified in `openapi_schema_map.md`
- [ ] `PUT /api/v1/settings/10dlc-profile` verified in `openapi_schema_map.md`
- [ ] **STEP 1**: `CustomerForm.tsx` — attestation checkbox added, `CustomerFormValues` extended, submit disabled when phone + no attestation
- [ ] **STEP 2**: `useCreateCustomer.ts` + `useUpdateCustomer.ts` — `sms_attestation_checked` passed in payload
- [ ] **STEP 3**: `use10DlcProfile.ts` + `useUpdate10DlcProfile.ts` hooks created
- [ ] **STEP 4**: `TenantDlcProfileForm.tsx` created — all fields, EIN masked display, success/error feedback, `RoleGate(settings.manage)`
- [ ] **STEP 5**: `TenantDlcProfileForm` wired into settings surface (same page as email branding)
- [ ] **STEP 6**: `dlcHandlers.ts` created — GET + PUT handlers with mock data
- [ ] **STEP 6**: `dlcHandlers` registered in `mocks/handlers/index.ts` barrel
- [ ] **STEP 7A**: `TenantDlcProfileForm.test.tsx` — 6+ unit tests pass (renders, pre-populates, RBAC, success, error, disabled)
- [ ] **STEP 7B**: `CustomerForm.test.tsx` — 5 new attestation tests added and pass
- [ ] **STEP 7C**: `dlc-profile.integration.test.tsx` — 4 integration tests pass
- [ ] Zero TypeScript errors (`check-types` passes)
- [ ] Zero ESLint warnings
- [ ] No regressions in existing `CustomerForm` tests (read existing tests before modifying the file)
- [ ] **Phase 2 FULL verification command passes** (`=== DLC-1 REACT FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== DLC-1 REACT FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count (before → after) documented in impl plan

---

## Completion Summary

After all Definition of Done items are complete, add a **Completion Summary** to `dev-docs/analysis/pilot-launch-plan.md` §DLC-1 using this format:

```markdown
### DLC-1 React — 10DLC Compliance Frontend: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)
**Build**: ✅ Pass — TypeScript errors: 0, ESLint warnings: 0

#### What Was Accomplished
- CustomerForm: attestation checkbox added with submit block
- TenantDlcProfileForm: 10DLC settings form with GET/PUT
- Settings page: 10DLC section wired
- MSW handlers: dlcHandlers.ts created + registered

#### Files Changed / Created
| File | Action |
|---|---|
| `frontend/apps/web/src/features/customers/components/CustomerForm.tsx` | Updated — attestation checkbox + submit guard |
| `frontend/apps/web/src/features/customers/hooks/useCreateCustomer.ts` | Updated — sms_attestation_checked in payload |
| `frontend/apps/web/src/features/customers/hooks/useUpdateCustomer.ts` | Updated — sms_attestation_checked in payload |
| `frontend/apps/web/src/features/sms-compliance/hooks/use10DlcProfile.ts` | Created |
| `frontend/apps/web/src/features/sms-compliance/hooks/useUpdate10DlcProfile.ts` | Created |
| `frontend/apps/web/src/features/sms-compliance/components/TenantDlcProfileForm.tsx` | Created |
| `frontend/apps/web/src/mocks/handlers/dlcHandlers.ts` | Created |
| `frontend/apps/web/src/mocks/handlers/index.ts` | Updated — dlcHandlers registered |
| ... | ... |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `features/sms-compliance/components/__tests__/TenantDlcProfileForm.test.tsx` | Unit | N | ✅ |
| `features/customers/components/__tests__/CustomerForm.test.tsx` | Unit (additions) | N | ✅ |
| `__tests__/batch_dlc_1/dlc-profile.integration.test.tsx` | Integration | N | ✅ |
```
