# MOB-B4 Batch Design — Calcs Tab: NEC Calculators (Dual-Path Architecture)

**Version**: 1.0
**Date**: 2026-06-06
**Batch**: MOB-B4
**Prerequisite Batches**: MOB-B0 ✅ (backend NEC API complete — `POST /api/v1/nec/calculate` confirmed)
**Estimated Effort**: 3–4 days (frontend only)
**Test Subfolder**: `apps/mobile/__tests__/batch_mob_b4/`
**Platform**: Mobile-only (Expo / React Native)
**Status**: Design complete — ready for React Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `frontend/apps/mobile/app/(tabs)/calcs.tsx` | 10-line stub: `<View><Text style={{fontSize:22,fontWeight:'500'}}>Calcs</Text></View>`. Replace entirely. |
| `frontend/apps/mobile/app/(tabs)/_layout.tsx` | **No calcs sub-route suppressions present**. All new calculator sub-screens must be added as `href: null` suppressions. Existing suppressions: `jobs/[jobId]/index`, `customers/[id]/index`, comms routes. |
| `backend/openapi_schema_map.md` §nec | ✅ `POST /api/v1/nec/calculate` confirmed. Request: `{ calc_type, inputs: {}, job_id?, idempotency_key? }`. Response: `{ log_id, calc_type, result: {}, nec_guide_version, nec_citation }`. ✅ `POST /api/v1/nec/calc-logs` (offline sync). ✅ `GET /api/v1/nec/calc-logs?job_id=&limit=&offset=` (saved calcs list). |
| `backend/services/nec_service.py` | **Source of truth for all offline TypeScript formulas.** Confirms exact input keys per calc_type (see §A.2). Confirms `NecCalcResult` shape: `{ calc_type, result_value, is_compliant, nec_article, nec_citation, **details }`. AWG tables, conduit tables, ampacity tables all extracted. |
| `frontend/apps/mobile/features/offline-sync/components/ConnectionStatePill.tsx` | Uses `useSyncQueueStore()` → `syncState.status`. `status === "idle"` + `pendingCount === 0` = fully synced. Does NOT expose a direct `isOnline` boolean. |
| `frontend/apps/mobile/features/offline-sync/store.ts` | `useSyncQueueStore` state: `{ status: "idle"\|"syncing"\|"error", pendingCount, lastSyncedAt }`. For NEC calcs, use React Native `NetInfo.fetch()` for live network check, not the sync store. |
| WatermelonDB model scan | Confirmed existing tables: `time_entries`, `expenses`, `job_notes`, `loto_checks`, `photos`, `change_orders`, `job_status_changes`, `voice_audio_queue`. **No `nec_calc_log` model exists** — must be created in this batch. |

### A.2 Critical Design Decision: Exact Input Keys Per Calc Type

Confirmed from `nec_service.py` — TypeScript offline functions must use the **same key names**:

**Voltage Drop**:
```
inputs.amperage (float, required, > 0)
inputs.distance_feet (float, required, > 0)
inputs.wire_gauge (str, required, e.g. "12 AWG" or "12")
inputs.voltage (float, default 120.0)
inputs.phase (int, 1 or 3, default 1)
```

**Conduit Fill**:
```
inputs.conduit_trade_size (str, required, e.g. "3/4")
inputs.conduit_type (str, "EMT"|"RMC"|"PVC40", default "EMT")
inputs.wire_gauge (str, required)
inputs.num_conductors (int, required, ≥ 1)
```

**Ampacity**:
```
inputs.wire_material (str, "copper"|"aluminum", default "copper")
inputs.wire_gauge (str, required)
inputs.temp_rating_c (int, 60|75|90, default 75)
inputs.conductor_count (int, default 3)
inputs.ambient_temp_c (float, default 30.0)
```

**API Response `result` object shape** (from `NecCalcResult.to_dict()`):
- All calcs: `{ calc_type, result_value, is_compliant, nec_article, nec_citation, ...details }`
- Voltage drop details: `{ voltage_drop, voltage_drop_pct, wire_gauge, wire_gauge_normalized, amperage, distance_feet, voltage, phase }`
- Conduit fill details: `{ fill_pct, max_fill_pct, total_fill_sq_in, conduit_area_sq_in, wire_gauge, wire_gauge_normalized, conduit_trade_size, conduit_type, num_conductors }`
- Ampacity details: `{ adjusted_ampacity, base_ampacity, temp_correction_factor, bundling_factor, temp_rating_c, conductor_count, ambient_temp_c, wire_gauge, wire_gauge_normalized }`

### A.3 Critical Design Decision: Online/Offline Detection

`ConnectionStatePill` does not expose an `isOnline` boolean. `useSyncQueueStore` tracks sync state, not network state.

**Resolution**: Use `@react-native-community/netinfo` for network detection:
```typescript
import NetInfo from "@react-native-community/netinfo";
const netState = await NetInfo.fetch();
const isOnline = netState.isConnected === true && netState.isInternetReachable !== false;
```

> **Before using**: Verify `@react-native-community/netinfo` is installed:
> ```bash
> grep "netinfo" frontend/apps/mobile/package.json
> ```
> If not installed, use `navigator.onLine` fallback (available in React Native). See §G.1.

### A.4 Critical Design Decision: New WatermelonDB Model Required

No `nec_calc_log` WatermelonDB model exists. Must create:
- Model file: `frontend/apps/mobile/database/models/NecCalcLog.ts`
- Table name: `"nec_calc_logs"` (plural, consistent with other models)
- Schema update: `frontend/apps/mobile/database/schema.ts`

The model stores offline calculation results with `localSyncStatus = 'pending'` and syncs to `POST /api/v1/nec/calc-logs` on reconnect via `SyncOrchestrator`.

---

## B. Migration Plan

### B.1 No Backend Migration Required

All 3 NEC API endpoints exist (confirmed — MOB-B0 complete):
- `POST /api/v1/nec/calculate` ✅
- `POST /api/v1/nec/calc-logs` ✅
- `GET /api/v1/nec/calc-logs` ✅

### B.2 WatermelonDB Model — `NecCalcLog`

**New file**: `frontend/apps/mobile/database/models/NecCalcLog.ts`

```typescript
// frontend/apps/mobile/database/models/NecCalcLog.ts
import { Model } from "@nozbe/watermelondb";
import { field, text, date, readonly, json } from "@nozbe/watermelondb/decorators";

export class NecCalcLog extends Model {
  static table = "nec_calc_logs";

  @text("calc_type") calcType!: string;            // 'voltage_drop' | 'conduit_fill' | 'ampacity'
  @json("inputs_json", (json) => json) inputsJson!: Record<string, unknown>;
  @json("result_json", (json) => json) resultJson!: Record<string, unknown>;
  @text("nec_guide_version") necGuideVersion!: string;  // "2023"
  @field("is_offline_calc") isOfflineCalc!: boolean;
  @text("idempotency_key") idempotencyKey!: string;    // UUID generated at capture
  @readonly @date("client_capture_at") clientCaptureAt!: Date;

  // Standard sync control fields (same as all SyncableModel instances)
  @text("local_sync_status") localSyncStatus!: string; // 'pending' | 'synced' | 'failed'
  @text("sync_error") syncError!: string | null;
  @field("retry_count") retryCount!: number;
}
```

**Schema addition** (`frontend/apps/mobile/database/schema.ts`):
```typescript
tableSchema({
  name: "nec_calc_logs",
  columns: [
    { name: "calc_type", type: "string" },
    { name: "inputs_json", type: "string" },    // JSONB stored as JSON string in WDB
    { name: "result_json", type: "string" },
    { name: "nec_guide_version", type: "string" },
    { name: "is_offline_calc", type: "boolean" },
    { name: "idempotency_key", type: "string" },
    { name: "client_capture_at", type: "number" },  // epoch ms
    { name: "local_sync_status", type: "string" },
    { name: "sync_error", type: "string", isOptional: true },
    { name: "retry_count", type: "number" },
  ],
}),
```

> **Read `database/schema.ts` fully before modifying** — follow the exact column definition pattern from existing tables.

### B.3 Route Structure

New routes under `app/(tabs)/calcs/`:
```
app/(tabs)/calcs/
  index.tsx              ← menu screen (replaces calcs.tsx stub)
  voltage-drop.tsx       ← Voltage Drop calculator
  conduit-fill.tsx       ← Conduit Fill calculator
  ampacity.tsx           ← Ampacity calculator
  saved-calcs.tsx        ← Saved Calculations list
```

**`calcs.tsx` stub** → replaced by importing from the new `calcs/` route group.

**`(tabs)/_layout.tsx`** — add suppressions for all new calcs sub-screens:
```typescript
{/* MOB-B4: Calcs sub-screens — suppress from tab bar */}
<Tabs.Screen name="calcs/voltage-drop" options={{ href: null }} />
<Tabs.Screen name="calcs/conduit-fill" options={{ href: null }} />
<Tabs.Screen name="calcs/ampacity" options={{ href: null }} />
<Tabs.Screen name="calcs/saved-calcs" options={{ href: null }} />
```

---

## C. Execution Order

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Verify `@react-native-community/netinfo` in `package.json` | `package.json` | None |
| 2 | Read `database/schema.ts` fully before modifying | `database/schema.ts` | None |
| 3 | Add `NecCalcLog` model file | `database/models/NecCalcLog.ts` | None |
| 4 | Add `nec_calc_logs` table schema | `database/schema.ts` | #3 |
| 5 | Create offline TypeScript engine (`nec-calcs/utils/`) | `features/nec-calcs/utils/calcVoltageDrop.ts`, `calcConduitFill.ts`, `calcAmpacity.ts` | None |
| 6 | Create `useNecCalculate` hook (dual-path) | `features/nec-calcs/hooks/useNecCalculate.ts` | #3, #5 |
| 7 | Create `useNecCalcLogs` hook (saved calcs list) | `features/nec-calcs/hooks/useNecCalcLogs.ts` | None |
| 8 | Create MSW NEC handlers | `mocks/handlers/necHandlers.ts` | None |
| 9 | Register handlers in `handlers/index.ts` | `mocks/handlers/index.ts` | #8 |
| 10 | Create `CalcsMenuScreen` component | `features/nec-calcs/components/CalcsMenuScreen.tsx` | None |
| 11 | Create `VoltageDrop` screen | `features/nec-calcs/components/VoltageDrop/VoltageDropScreen.tsx` | #6 |
| 12 | Create `ConduitFill` screen | `features/nec-calcs/components/ConduitFill/ConduitFillScreen.tsx` | #6 |
| 13 | Create `Ampacity` screen | `features/nec-calcs/components/Ampacity/AmpacityScreen.tsx` | #6 |
| 14 | Create `SavedCalcs` screen | `features/nec-calcs/components/SavedCalcsScreen.tsx` | #7 |
| 15 | Create `CalcResultDisplay` shared component | `features/nec-calcs/components/CalcResultDisplay.tsx` | None |
| 16 | Create `OfflineBanner` component | `features/nec-calcs/components/OfflineBanner.tsx` | None |
| 17 | Replace `calcs.tsx` stub | `app/(tabs)/calcs.tsx` → imports `CalcsMenuScreen` | #10 |
| 18 | Create `calcs/` sub-routes | `app/(tabs)/calcs/voltage-drop.tsx`, `conduit-fill.tsx`, `ampacity.tsx`, `saved-calcs.tsx` | #11–#14 |
| 19 | Update `_layout.tsx` — add calcs sub-screen suppressions | `app/(tabs)/_layout.tsx` | #18 |
| 20 | Write unit + integration tests | `__tests__/batch_mob_b4/` + co-located unit tests | #11–#14 |
| 21 | Regression check + TypeScript + lint | — | #20 |

---

## D. New API Endpoints Consumed

### D.1 `POST /api/v1/nec/calculate` (confirmed — MOB-B0)

**Used by**: `useNecCalculate` hook (online path)

**Request**:
```json
{
  "calc_type": "voltage_drop",
  "inputs": {
    "amperage": 20,
    "distance_feet": 100,
    "wire_gauge": "12 AWG",
    "voltage": 120,
    "phase": 1
  },
  "idempotency_key": "uuid"
}
```

**Response 201** (`NecCalculateResponse`):
```json
{
  "log_id": "uuid",
  "calc_type": "voltage_drop",
  "result": {
    "calc_type": "voltage_drop",
    "result_value": 3.9478,
    "is_compliant": false,
    "nec_article": "NEC 210.19(A)(1)",
    "nec_citation": "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
    "voltage_drop": 3.9478,
    "voltage_drop_pct": 3.2898,
    "wire_gauge": "12 AWG",
    "amperage": 20,
    "distance_feet": 100,
    "voltage": 120,
    "phase": 1
  },
  "nec_guide_version": "2023",
  "nec_citation": "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended"
}
```

### D.2 `POST /api/v1/nec/calc-logs` (confirmed — MOB-B0)

**Used by**: `SyncOrchestrator` (via `useNecCalculate` hook writing to WatermelonDB)

**Called automatically on reconnect** when offline calcs with `localSyncStatus = 'pending'` exist.

```json
{
  "calc_type": "voltage_drop",
  "inputs": { ... },
  "result": { ... },
  "nec_guide_version": "2023",
  "is_offline_calc": true,
  "client_capture_at": "2026-06-06T14:32:00Z",
  "idempotency_key": "uuid"
}
```

### D.3 `GET /api/v1/nec/calc-logs` (confirmed — MOB-B0)

**Used by**: `useNecCalcLogs` hook (Saved Calculations screen)

```
GET /api/v1/nec/calc-logs?limit=50&offset=0
```

**Response**: `[{ id, calc_type, nec_guide_version, inputs_json, result_json, is_offline_calc, client_capture_at, job_id }]`

---

## E. Pattern Reuse Decisions

### E.1 Dual-Path Architecture Pattern

```
User submits calc form
        ↓
Is device online? (NetInfo.fetch())
        ↓ YES                    ↓ NO
apiClient.post(                TypeScript
  /api/v1/nec/calculate)       offline engine
        ↓                            ↓
  Result displayed         Result displayed
  Saved to server          + "⚠️ Offline" banner
                           Saved to WatermelonDB
                           with localSyncStatus='pending'
                                     ↓
                              SyncOrchestrator
                              on reconnect:
                              POST /api/v1/nec/calc-logs
```

### E.2 Offline Write Pattern (from MOB-B2 / FE-B7)

```typescript
// Same idempotency key generation as all offline write hooks
function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Write to WatermelonDB
const log = await database.write(async () => {
  return database.get<NecCalcLog>("nec_calc_logs").create((record) => {
    record.calcType = calcType;
    record.inputsJson = inputs;
    record.resultJson = result;
    record.necGuideVersion = "2023";
    record.isOfflineCalc = true;
    record.idempotencyKey = idempotencyKey;
    record.clientCaptureAt = new Date();
    record.localSyncStatus = "pending";
    record.syncError = null;
    record.retryCount = 0;
  });
});
```

### E.3 `NavigateFromCalcsMenu` Pattern

Calcs menu → sub-screen navigation uses `router.push`:
```typescript
router.push("/(tabs)/calcs/voltage-drop" as any);
router.push("/(tabs)/calcs/conduit-fill" as any);
router.push("/(tabs)/calcs/ampacity" as any);
router.push("/(tabs)/calcs/saved-calcs" as any);
```

### E.4 TypeScript Offline Engine Mirrors `nec_service.py`

The offline TypeScript functions in `features/nec-calcs/utils/` must produce identical results to `nec_service.py`. They use the same lookup tables copied from the Python service. See §F.3.

---

## F. Shared Module Interfaces

### F.1 `useNecCalculate` — New Hook

```typescript
// frontend/apps/mobile/features/nec-calcs/hooks/useNecCalculate.ts

export interface NecCalcResult {
  calc_type: string;
  result_value: number;
  is_compliant: boolean;
  nec_article: string;
  nec_citation: string;
  [key: string]: unknown;  // calc-type specific detail fields
}

export interface NecCalcState {
  result: NecCalcResult | null;
  isOfflineCalc: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useNecCalculate() {
  const [state, setState] = useState<NecCalcState>({
    result: null,
    isOfflineCalc: false,
    isLoading: false,
    error: null,
  });

  const calculate = useCallback(async (
    calcType: "voltage_drop" | "conduit_fill" | "ampacity",
    inputs: Record<string, unknown>,
  ) => {
    setState(s => ({ ...s, isLoading: true, error: null }));

    // 1. Check connectivity
    const isOnline = await checkIsOnline(); // NetInfo.fetch() — see §G.1

    if (isOnline) {
      // Online path
      try {
        const idempotencyKey = generateIdempotencyKey();
        const { data } = await apiClient.post("/api/v1/nec/calculate", {
          calc_type: calcType,
          inputs,
          idempotency_key: idempotencyKey,
        });
        setState({ result: data.result, isOfflineCalc: false, isLoading: false, error: null });
      } catch (err) {
        // API call failed — fallback to offline engine
        await runOffline(calcType, inputs, setState);
      }
    } else {
      // Offline path
      await runOffline(calcType, inputs, setState);
    }
  }, []);

  return { ...state, calculate };
}

async function runOffline(
  calcType: string,
  inputs: Record<string, unknown>,
  setState: ...,
) {
  try {
    const result = calculateOffline(calcType, inputs);  // from nec-calcs/utils/
    const idempotencyKey = generateIdempotencyKey();

    // Save to WatermelonDB
    await database.write(async () => {
      database.get<NecCalcLog>("nec_calc_logs").create((record) => {
        record.calcType = calcType;
        record.inputsJson = inputs;
        record.resultJson = result;
        record.necGuideVersion = "2023";
        record.isOfflineCalc = true;
        record.idempotencyKey = idempotencyKey;
        record.clientCaptureAt = new Date();
        record.localSyncStatus = "pending";
        record.syncError = null;
        record.retryCount = 0;
      });
    });

    setState({ result, isOfflineCalc: true, isLoading: false, error: null });
  } catch (err) {
    setState(s => ({ ...s, isLoading: false, error: err instanceof Error ? err.message : "Calculation failed" }));
  }
}
```

### F.2 `useNecCalcLogs` — New Hook

```typescript
// frontend/apps/mobile/features/nec-calcs/hooks/useNecCalcLogs.ts

export interface SavedNecCalcLog {
  id: string;
  calc_type: string;
  nec_guide_version: string;
  inputs_json: Record<string, unknown>;
  result_json: Record<string, unknown>;
  is_offline_calc: boolean;
  client_capture_at: string | null;
  job_id: string | null;
}

export function useNecCalcLogs() {
  return useQuery({
    queryKey: ["nec-calc-logs"],
    queryFn: async () => {
      const res = await apiClient.get<SavedNecCalcLog[]>("/api/v1/nec/calc-logs", {
        params: { limit: 50 }
      });
      return res.data;
    },
    staleTime: 30_000,
  });
}
```

### F.3 Offline TypeScript Engine — `features/nec-calcs/utils/`

Three pure function modules, each a TypeScript port of the corresponding `nec_service.py` function:

**`calcVoltageDrop.ts`**:
```typescript
// frontend/apps/mobile/features/nec-calcs/utils/calcVoltageDrop.ts
// NEC 210.19(A)(1) Informational Note 4

// Lookup tables copied verbatim from nec_service.py _AWG_CIRCULAR_MILS
const AWG_CIRCULAR_MILS: Record<string, number> = {
  "14": 4110.0, "12": 6530.0, "10": 10380.0, "8": 16510.0,
  "6": 26240.0, "4": 41740.0, "3": 52620.0, "2": 66360.0,
  "1": 83690.0, "1/0": 105600.0, "2/0": 133100.0, "3/0": 167800.0,
  "4/0": 211600.0, "250": 250000.0, "300": 300000.0, "350": 350000.0,
  "400": 400000.0, "500": 500000.0,
};

const K_COPPER = 12.9;

export interface VoltageDropInputs {
  amperage: number;
  distance_feet: number;
  wire_gauge: string;
  voltage?: number;      // default 120
  phase?: number;        // default 1
}

export interface VoltageDropResult {
  calc_type: "voltage_drop";
  result_value: number;  // voltage_drop
  is_compliant: boolean;
  nec_article: string;
  nec_citation: string;
  voltage_drop: number;
  voltage_drop_pct: number;
  wire_gauge: string;
  wire_gauge_normalized: string;
  amperage: number;
  distance_feet: number;
  voltage: number;
  phase: number;
}

export function calcVoltageDrop(inputs: VoltageDropInputs): VoltageDropResult {
  // Mirror _calc_voltage_drop() from nec_service.py exactly
  const { amperage, distance_feet, wire_gauge, voltage = 120, phase = 1 } = inputs;
  const normalized = normalizeGauge(wire_gauge);
  const circularMils = AWG_CIRCULAR_MILS[normalized];
  if (!circularMils) throw new Error(`Unknown wire gauge: ${wire_gauge}`);
  const multiplier = phase === 3 ? 1.732 : 2.0;
  const voltageDrop = (multiplier * K_COPPER * amperage * distance_feet) / circularMils;
  const voltageDropPct = (voltageDrop / voltage) * 100;
  const isCompliant = voltageDropPct <= 3.0;
  return {
    calc_type: "voltage_drop", result_value: round(voltageDrop, 4),
    is_compliant: isCompliant,
    nec_article: "NEC 210.19(A)(1)",
    nec_citation: "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
    voltage_drop: round(voltageDrop, 4), voltage_drop_pct: round(voltageDropPct, 4),
    wire_gauge, wire_gauge_normalized: normalized, amperage, distance_feet, voltage, phase,
  };
}
```

Similarly for `calcConduitFill.ts` and `calcAmpacity.ts`.

**Shared `nec-calcs/utils/index.ts`**:
```typescript
export function calculateOffline(calcType: string, inputs: Record<string, unknown>): NecCalcResult {
  switch (calcType) {
    case "voltage_drop": return calcVoltageDrop(inputs as VoltageDropInputs);
    case "conduit_fill": return calcConduitFill(inputs as ConduitFillInputs);
    case "ampacity": return calcAmpacity(inputs as AmpacityInputs);
    default: throw new Error(`Unknown calc_type: ${calcType}`);
  }
}
```

### F.4 `CalcsMenuScreen` — New Component

```typescript
// frontend/apps/mobile/features/nec-calcs/components/CalcsMenuScreen.tsx
```

**Renders** a top-aligned `SafeAreaView` + `ScrollView` with 5 menu rows:

```
┌──────────────────────────────────┐
│  Calcs                            │
│ ─────────────────────────────── │
│  ⚡ Voltage Drop Calculator    > │
│  📐 Conduit Fill Calculator    > │
│  🔌 Ampacity Calculator        > │
│  📚 NEC 2023 Reference          > │  (future — show disabled/placeholder for MVP)
│  🕐 Saved Calculations         > │
└──────────────────────────────────┘
```

> **NEC Reference row**: Navigation to a PDF/markdown viewer is out of scope for MVP. Render it as a non-interactive row with `(Coming soon)` label or omit it entirely. See §G.2.

### F.5 Calculator Screens (`VoltageDrop`, `ConduitFill`, `Ampacity`)

Each calculator screen follows the same structure:

```typescript
// Pattern for all 3 calculator screens
export function VoltageDropScreen() {
  const { result, isOfflineCalc, isLoading, error, calculate } = useNecCalculate();

  // Form state
  const [amperage, setAmperage] = useState("");
  const [distanceFeet, setDistanceFeet] = useState("");
  const [wireGauge, setWireGauge] = useState("12");
  const [voltage, setVoltage] = useState("120");
  const [phase, setPhase] = useState<1 | 3>(1);

  const handleCalculate = async () => {
    await calculate("voltage_drop", {
      amperage: parseFloat(amperage),
      distance_feet: parseFloat(distanceFeet),
      wire_gauge: wireGauge,
      voltage: parseFloat(voltage),
      phase,
    });
  };

  return (
    <SafeAreaView>
      <View style={styles.header}>
        <Pressable onPress={() => router.back()}>← Calcs</Pressable>
        <Text style={styles.title}>Voltage Drop</Text>
      </View>
      {isOfflineCalc && <OfflineBanner />}
      <ScrollView>
        {/* Input form fields */}
        <TextInput label="Amps (A)" value={amperage} onChangeText={setAmperage} keyboardType="numeric" />
        <TextInput label="Distance (ft)" value={distanceFeet} onChangeText={setDistanceFeet} keyboardType="numeric" />
        {/* Wire gauge picker: "14", "12", "10", "8", "6", "4", "3", "2", "1", "1/0", "2/0", "3/0", "4/0", "250", "300", "350", "400", "500" */}
        {/* Phase picker: Single (1) | Three (3) */}
        <Pressable onPress={handleCalculate}><Text>Calculate</Text></Pressable>
        {isLoading && <ActivityIndicator />}
        {error && <Text style={styles.error}>{error}</Text>}
        {result && <CalcResultDisplay result={result} />}
      </ScrollView>
    </SafeAreaView>
  );
}
```

### F.6 `CalcResultDisplay` — Shared Component

```typescript
// frontend/apps/mobile/features/nec-calcs/components/CalcResultDisplay.tsx
interface CalcResultDisplayProps {
  result: NecCalcResult;
  testID?: string;
}
```

**Renders**:
- Pass/fail badge: green "✓ PASS" or red "✗ FAIL"  based on `result.is_compliant`
- Primary value: formatted `result_value` with units (voltage drop in V, fill%, ampacity in A)
- NEC citation text: `result.nec_citation`
- Key details from `result` (calc-type specific)

### F.7 `OfflineBanner` — New Component

```typescript
// frontend/apps/mobile/features/nec-calcs/components/OfflineBanner.tsx
```

**Renders** (when `isOfflineCalc === true`):
```
⚠️  Offline — using NEC 2023 code formulas
     Result saved locally and will sync when online
```
- Background: `colors.alert[50]`, border: `colors.alert[200]`
- No mention of "verify online" — user decides when to recalculate

### F.8 `SavedCalcsScreen` — New Component

Lists all previous NEC calculations from `useNecCalcLogs`. Each row shows:
- `calc_type` badge (Voltage Drop / Conduit Fill / Ampacity)
- `result_value` with unit
- `is_compliant` pass/fail indicator
- `is_offline_calc` chip if applicable
- Formatted `created_at` / `client_capture_at`

---

## G. Open Questions Resolved

### G.1 — Online/Offline Detection: `NetInfo` vs Fallback

**Problem**: `ConnectionStatePill` doesn't expose `isOnline`. `useSyncQueueStore` tracks sync state, not network state.

**Resolution**:
1. Check `grep "netinfo" frontend/apps/mobile/package.json` in pre-work
2. If `@react-native-community/netinfo` found: `const state = await NetInfo.fetch(); const isOnline = state.isConnected === true && state.isInternetReachable !== false;`
3. If NOT found: Use `navigator.onLine` (available in React Native): `const isOnline = navigator.onLine ?? false;`
4. Add `// TODO: prefer NetInfo over navigator.onLine when available` comment

### G.2 — NEC Reference Row

**Resolution**: Render the "NEC 2023 Reference" menu row as a static placeholder:
```typescript
<View style={[styles.menuRow, styles.disabled]} testID="nec-reference-row">
  <Text style={styles.menuLabel}>📚 NEC 2023 Reference</Text>
  <Text style={styles.comingSoon}>Coming soon</Text>
</View>
```
No navigation — just shows the row as non-interactive. This satisfies the impl plan's §8 menu spec without requiring a PDF viewer.

### G.3 — WatermelonDB `NecCalcLog` Column Types for JSONB

**Problem**: WatermelonDB doesn't have native JSONB column type.

**Resolution**: Store `inputs_json` and `result_json` as `{ type: "string" }` columns in schema. Use `@json` decorator for automatic serialization/deserialization. This is how complex data is stored in WatermelonDB (see `VoiceAudioQueue` pattern if applicable).

### G.4 — `SyncOrchestrator` Integration for `nec_calc_logs`

**Problem**: The `SyncOrchestrator` needs to know about the new `nec_calc_logs` table to sync pending offline calcs.

**Resolution**: Read `frontend/apps/mobile/database/sync/orchestrator.ts` before implementing. Add `nec_calc_logs` to the orchestrator's push configuration using the same pattern as other offline-write tables. The `POST /api/v1/nec/calc-logs` endpoint is the sync target.

> **If `orchestrator.ts` complexity is high**: As a fallback, implement a simpler retry mechanism in `useNecCalculate` that uses `useFocusEffect` to attempt sync of pending WatermelonDB records when the user returns to the Calcs screen. This avoids modifying the orchestrator for MVP.

### G.5 — Wire Gauge Picker vs Free-Text Input

**Resolution**: Use a picker/dropdown (not free text) for wire gauge. Display options as "14 AWG", "12 AWG", etc. The underlying value sent to the API is just the number (e.g., "12"). This prevents invalid gauge values that would cause the API or offline engine to throw errors.

Supported gauges (from `_AWG_CIRCULAR_MILS` in `nec_service.py`): `14, 12, 10, 8, 6, 4, 3, 2, 1, 1/0, 2/0, 3/0, 4/0, 250, 300, 350, 400, 500`.

### G.6 — Conduit Size Picker Options

Use picker for `conduit_trade_size`. EMT options (from `_CONDUIT_AREA_SQ_IN` in `nec_service.py`): `"1/2", "3/4", "1", "1-1/4", "1-1/2", "2", "2-1/2", "3", "3-1/2", "4"`. Same for RMC and PVC40 — same sizes.

---

## H. Surface Mockup Reference

### H.1 Calcs Tab Menu

```
┌──────────────────────────────────┐
│  Calcs                            │  ← SafeAreaView top
│ ─────────────────────────────── │
│  ⚡ Voltage Drop Calculator    > │
│ ─────────────────────────────── │
│  📐 Conduit Fill Calculator    > │
│ ─────────────────────────────── │
│  🔌 Ampacity Calculator        > │
│ ─────────────────────────────── │
│  📚 NEC 2023 Reference           │  ← disabled, "Coming soon"
│ ─────────────────────────────── │
│  🕐 Saved Calculations         > │
└──────────────────────────────────┘
```

### H.2 Voltage Drop Calculator

```
┌──────────────────────────────────┐
│ ← Calcs    ⚡ Voltage Drop        │  ← header
│ ─────────────────────────────── │
│ ⚠️ Offline — NEC 2023 formulas   │  ← OfflineBanner (when offline)
│ ─────────────────────────────── │
│  Amps (A)                        │
│  [20                         ]   │
│  Distance (ft)                   │
│  [100                        ]   │
│  Wire Gauge                      │
│  [12 AWG              ▼     ]   │
│  Voltage (V)                     │
│  [120                        ]   │
│  Phase   ⦿ Single    ○ Three     │
│                                   │
│  [ Calculate ]                   │
│ ─────────────────────────────── │
│                                   │
│  ✗ FAIL   Voltage Drop: 3.29 V   │  ← CalcResultDisplay
│  3.29% drop (limit: 3.0%)        │
│  NEC 210.19(A)(1) Informational  │
│  Note 4 — Voltage drop ≤ 3%     │
│  recommended                     │
└──────────────────────────────────┘
```

---

## I. Component Manifest

| Component / Hook / Util | File Path | Action | Batch |
|:---|:---|:---|:---|
| `NecCalcLog` model | `apps/mobile/database/models/NecCalcLog.ts` | **New** | MOB-B4 |
| `database/schema.ts` | `apps/mobile/database/schema.ts` | **Modify** — add `nec_calc_logs` table | MOB-B4 |
| `calcVoltageDrop` | `apps/mobile/features/nec-calcs/utils/calcVoltageDrop.ts` | **New** — pure function | MOB-B4 |
| `calcConduitFill` | `apps/mobile/features/nec-calcs/utils/calcConduitFill.ts` | **New** — pure function | MOB-B4 |
| `calcAmpacity` | `apps/mobile/features/nec-calcs/utils/calcAmpacity.ts` | **New** — pure function | MOB-B4 |
| `calculateOffline` | `apps/mobile/features/nec-calcs/utils/index.ts` | **New** — router | MOB-B4 |
| `useNecCalculate` | `apps/mobile/features/nec-calcs/hooks/useNecCalculate.ts` | **New** — dual-path hook | MOB-B4 |
| `useNecCalcLogs` | `apps/mobile/features/nec-calcs/hooks/useNecCalcLogs.ts` | **New** | MOB-B4 |
| `CalcResultDisplay` | `apps/mobile/features/nec-calcs/components/CalcResultDisplay.tsx` | **New** — shared | MOB-B4 |
| `OfflineBanner` | `apps/mobile/features/nec-calcs/components/OfflineBanner.tsx` | **New** | MOB-B4 |
| `CalcsMenuScreen` | `apps/mobile/features/nec-calcs/components/CalcsMenuScreen.tsx` | **New** | MOB-B4 |
| `VoltageDropScreen` | `apps/mobile/features/nec-calcs/components/VoltageDrop/VoltageDropScreen.tsx` | **New** | MOB-B4 |
| `ConduitFillScreen` | `apps/mobile/features/nec-calcs/components/ConduitFill/ConduitFillScreen.tsx` | **New** | MOB-B4 |
| `AmpacityScreen` | `apps/mobile/features/nec-calcs/components/Ampacity/AmpacityScreen.tsx` | **New** | MOB-B4 |
| `SavedCalcsScreen` | `apps/mobile/features/nec-calcs/components/SavedCalcsScreen.tsx` | **New** | MOB-B4 |
| `calcs.tsx` (stub) | `apps/mobile/app/(tabs)/calcs.tsx` | **Replace** — import `CalcsMenuScreen` | MOB-B4 |
| `calcs/voltage-drop.tsx` | `apps/mobile/app/(tabs)/calcs/voltage-drop.tsx` | **New** — route file | MOB-B4 |
| `calcs/conduit-fill.tsx` | `apps/mobile/app/(tabs)/calcs/conduit-fill.tsx` | **New** — route file | MOB-B4 |
| `calcs/ampacity.tsx` | `apps/mobile/app/(tabs)/calcs/ampacity.tsx` | **New** — route file | MOB-B4 |
| `calcs/saved-calcs.tsx` | `apps/mobile/app/(tabs)/calcs/saved-calcs.tsx` | **New** — route file | MOB-B4 |
| `(tabs)/_layout.tsx` | `apps/mobile/app/(tabs)/_layout.tsx` | **Modify** — add 4 calcs sub-screen suppressions | MOB-B4 |
| `necHandlers.ts` | `apps/mobile/mocks/handlers/necHandlers.ts` | **New** — MSW fixtures | MOB-B4 |
| `mocks/handlers/index.ts` | `apps/mobile/mocks/handlers/index.ts` | **Modify** — register necHandlers | MOB-B4 |

---

## J. Test Plan

**Test subfolder**: `apps/mobile/__tests__/batch_mob_b4/`

### J.1 Unit Tests — Pure Calculation Functions

| Test | File | Assertion |
|:---|:---|:---|
| `calcVoltageDrop` 12 AWG, 100ft, 20A, 120V, single | `calcVoltageDrop.test.ts` | `voltage_drop_pct ≈ 3.29%`, `is_compliant=false` |
| `calcVoltageDrop` three-phase √3 factor | `calcVoltageDrop.test.ts` | Multiplier 1.732 applied correctly |
| `calcVoltageDrop` pass when ≤ 3% | `calcVoltageDrop.test.ts` | 12 AWG, 50ft, 10A, 120V → `is_compliant=true` |
| `calcVoltageDrop` unknown gauge throws | `calcVoltageDrop.test.ts` | `wire_gauge="7 AWG"` → `Error` |
| `calcConduitFill` EMT 3/4", 3× #12 | `calcConduitFill.test.ts` | `fill_pct = 3 × 0.0133 / 0.533 × 100 ≈ 7.5%`, `is_compliant=true` |
| `calcConduitFill` 3+ wires >40% fails | `calcConduitFill.test.ts` | Many conductors → `is_compliant=false` |
| `calcConduitFill` 2-wire 31% limit | `calcConduitFill.test.ts` | `num_conductors=2`, limit is 31% |
| `calcConduitFill` 1-wire 53% limit | `calcConduitFill.test.ts` | `num_conductors=1`, limit is 53% |
| `calcAmpacity` #12 THHN 75°C, 30°C ambient, 3 conductors | `calcAmpacity.test.ts` | `adjusted_ampacity = 25.0` (no derating) |
| `calcAmpacity` bundling derating 4–6 conductors → 80% | `calcAmpacity.test.ts` | `conductor_count=4` → `bundling_factor=0.80` |
| `calculateOffline` routes to correct function | `index.test.ts` | `calcType="voltage_drop"` → calls `calcVoltageDrop` |

### J.2 Unit Tests — `useNecCalculate` Hook

| Test | File | Assertion |
|:---|:---|:---|
| Online path calls `POST /api/v1/nec/calculate` | `useNecCalculate.test.ts` | With network → MSW handler called |
| Online path returns result from API | `useNecCalculate.test.ts` | API response → `result` state set, `isOfflineCalc=false` |
| Offline path uses TypeScript engine | `useNecCalculate.test.ts` | No network → TypeScript calc used, `isOfflineCalc=true` |
| Offline result saved to WatermelonDB | `useNecCalculate.test.ts` | After offline calc → `nec_calc_logs` WDB table has new record |
| Offline result has `localSyncStatus="pending"` | `useNecCalculate.test.ts` | WDB record → `localSyncStatus === 'pending'` |
| API failure fallback to offline | `useNecCalculate.test.ts` | MSW returns 500 → offline engine used |

### J.3 Integration Tests

| Test | File | Assertion |
|:---|:---|:---|
| Calcs tab renders menu | `batch_mob_b4/calcs-tab.integration.test.tsx` | 5 menu rows visible, no "Calcs" centered text |
| Tap Voltage Drop → navigates | `batch_mob_b4/calcs-tab.integration.test.tsx` | `router.push` to `calcs/voltage-drop` |
| Voltage Drop calculates online | `batch_mob_b4/voltage-drop.integration.test.tsx` | Fill form → submit → API called → result displayed |
| Offline banner shown when offline | `batch_mob_b4/voltage-drop.integration.test.tsx` | No network → "⚠️ Offline" banner visible |
| Saved Calcs renders logs | `batch_mob_b4/saved-calcs.integration.test.tsx` | MSW returns 2 logs → 2 rows visible |
| `CalcResultDisplay` shows pass/fail | `batch_mob_b4/calc-result.integration.test.tsx` | `is_compliant=true` → "✓ PASS" visible |

### J.4 Regression Tests

| Test | Assertion |
|:---|:---|
| `_layout.tsx` existing suppressions intact | `jobs/[jobId]/index`, `customers/[id]/index`, comms routes still suppressed |
| All existing MOB-B1 through MOB-B5 tests pass | No regressions from adding `nec_calc_logs` WatermelonDB schema |

---

## Design Doc Quality Gate Checklist

- [x] `calcs.tsx` stub confirmed (10-line centered stub) — replace entirely
- [x] `_layout.tsx` confirmed — NO calcs sub-route suppressions exist; must add 4 new ones
- [x] `POST /api/v1/nec/calculate` confirmed in schema map — request + response shapes documented §D.1
- [x] `POST /api/v1/nec/calc-logs` confirmed — offline sync endpoint shapes documented §D.2
- [x] `GET /api/v1/nec/calc-logs` confirmed — saved calcs list endpoint documented §D.3
- [x] Exact `nec_service.py` input keys confirmed per calc_type — §A.2 (TypeScript engine must mirror these)
- [x] `NecCalcResult.to_dict()` shape confirmed — §A.2
- [x] No WatermelonDB `nec_calc_log` model exists — new model + schema addition required §B.2
- [x] Online/offline detection: `NetInfo` vs `navigator.onLine` fallback documented §G.1
- [x] NEC Reference row: disabled "Coming soon" — no PDF viewer required §G.2
- [x] WDB JSONB columns stored as string + `@json` decorator §G.3
- [x] SyncOrchestrator integration: read `orchestrator.ts` first; fallback to focus-based retry §G.4
- [x] Wire gauge picker (not free text) — prevents invalid gauge errors §G.5
- [x] Conduit size picker — EMT/RMC/PVC40 sizes from lookup tables §G.6
- [x] Offline banner: no "verify online" language — user decides §F.7
- [x] Dual-path architecture: online → API, offline fallback → TypeScript engine §E.1
- [x] All TypeScript offline functions mirror `nec_service.py` formulas exactly §F.3
- [x] Infrastructure constraint: zero cost impact
