# Implementation Prompt: MOB-B4 — Calcs Tab: NEC Calculators (Dual-Path Architecture)

**Mode**: Pilot React Engineer
**Batch**: MOB-B4
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B4
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b4-design.md`
**Estimated session**: 3–4 days
**Platform**: Mobile only (`apps/mobile`)
**Backend companion**: MOB-B0 ✅ complete — `POST /api/v1/nec/calculate` confirmed in schema map

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:
- **`dev-docs/architecture-design/batch-designs/batch-mob-b4-design.md`** — every section (A–J)
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule A**: API endpoint shapes already confirmed from `openapi_schema_map.md` — use the shapes in §D of the design doc. Do NOT re-verify.
- **Rule B**: TypeScript offline functions MUST mirror `nec_service.py` exactly (same input keys, same formulas, same lookup tables). Read `backend/services/nec_service.py` in full before writing any offline function.
- **Rule C**: All online API calls use `apiClient` — not raw `fetch()`.
- **Rule D**: Read `database/schema.ts` and all existing model files before creating the new `NecCalcLog` model.
- **Rule E**: No new npm dependencies without confirmation. Check `netinfo` availability first (pre-work).

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record exact test count before any changes.

---

## Pre-Work: Read These Files First

```bash
# Confirm MOB-B0 is complete
grep "nec/calculate" backend/openapi_schema_map.md | head -5
# Expected: shows POST /api/v1/nec/calculate

# Read nec_service.py fully — TypeScript offline engine must mirror this exactly
cat backend/services/nec_service.py

# Read existing WatermelonDB schema before adding new table
cat frontend/apps/mobile/database/schema.ts

# Read an existing model for pattern reference
cat frontend/apps/mobile/database/models/LotoCheck.ts
cat frontend/apps/mobile/database/models/Expense.ts

# Check if netinfo is installed
grep "netinfo" frontend/apps/mobile/package.json

# Read SyncOrchestrator to understand how to add nec_calc_logs sync
cat frontend/apps/mobile/database/sync/orchestrator.ts

# Read _layout.tsx — must add 4 calcs sub-screen suppressions
cat frontend/apps/mobile/app/(tabs)/_layout.tsx

# MSW handler registration
cat frontend/apps/mobile/mocks/handlers/index.ts

# Styling tokens
cat frontend/apps/mobile/constants/style-constants.ts
```

---

## Context: What This Batch Does

Replaces the `calcs.tsx` stub with a 5-screen NEC calculator suite (menu + 3 calculators + saved calcs). Implements dual-path architecture: online uses `POST /api/v1/nec/calculate`, offline uses TypeScript NEC 2023 formulas that mirror `nec_service.py`.

| Item | Change |
|---|---|
| `calcs.tsx` | Replace stub with `<CalcsMenuScreen />` |
| `(tabs)/_layout.tsx` | Add 4 new calcs sub-screen suppressions |
| New: `database/models/NecCalcLog.ts` | WatermelonDB model for offline calc storage |
| New: `database/schema.ts` | Add `nec_calc_logs` table schema |
| New: `features/nec-calcs/utils/` | 3 TypeScript NEC formula modules + router |
| New: `useNecCalculate` hook | Dual-path: online API / offline TypeScript |
| New: `useNecCalcLogs` hook | Fetches saved calcs from `GET /api/v1/nec/calc-logs` |
| New: 4 calculator screens | VoltageDropScreen, ConduitFillScreen, AmpacityScreen, SavedCalcsScreen |
| New: `CalcsMenuScreen` | Menu with 5 rows |
| New: `CalcResultDisplay` | Shared pass/fail result component |
| New: `OfflineBanner` | "⚠️ Offline — using NEC 2023 code formulas" |
| New: 4 route files | `calcs/voltage-drop.tsx`, `conduit-fill.tsx`, `ampacity.tsx`, `saved-calcs.tsx` |
| New: `necHandlers.ts` | MSW fixtures for NEC API endpoints |

---

## Step 1: Create `NecCalcLog` WatermelonDB Model

**File**: `frontend/apps/mobile/database/models/NecCalcLog.ts`

Read `database/models/LotoCheck.ts` and `database/models/Expense.ts` for the pattern. The model extends `Model` (not `SyncableModel` — `SyncableModel` may not exist; check what existing models extend).

```typescript
import { Model } from "@nozbe/watermelondb";
import { field, text, date, json, readonly } from "@nozbe/watermelondb/decorators";

export class NecCalcLog extends Model {
  static table = "nec_calc_logs";

  @text("calc_type") calcType!: string;
  // JSON fields stored as string in WatermelonDB
  @json("inputs_json", (rawJson: unknown) => rawJson ?? {})
  inputsJson!: Record<string, unknown>;
  @json("result_json", (rawJson: unknown) => rawJson ?? {})
  resultJson!: Record<string, unknown>;
  @text("nec_guide_version") necGuideVersion!: string;
  @field("is_offline_calc") isOfflineCalc!: boolean;
  @text("idempotency_key") idempotencyKey!: string;
  @readonly @date("client_capture_at") clientCaptureAt!: Date;
  @text("local_sync_status") localSyncStatus!: string;
  @text("sync_error") syncError!: string | null;
  @field("retry_count") retryCount!: number;
}
```

> **Verify `@json` decorator availability** — read `database/models/` for any existing model that uses `@json`. If `@json` is not used anywhere, use `@text` for `inputs_json` and `result_json` and serialize/deserialize manually with `JSON.stringify`/`JSON.parse`.

---

## Step 2: Add `nec_calc_logs` Schema Entry

**File**: `frontend/apps/mobile/database/schema.ts`

Read the file first. Add the new table following the exact pattern of existing tables:

```typescript
tableSchema({
  name: "nec_calc_logs",
  columns: [
    { name: "calc_type", type: "string" },
    { name: "inputs_json", type: "string" },
    { name: "result_json", type: "string" },
    { name: "nec_guide_version", type: "string" },
    { name: "is_offline_calc", type: "boolean" },
    { name: "idempotency_key", type: "string" },
    { name: "client_capture_at", type: "number" },
    { name: "local_sync_status", type: "string" },
    { name: "sync_error", type: "string", isOptional: true },
    { name: "retry_count", type: "number" },
  ],
}),
```

> **Schema version**: WatermelonDB requires incrementing the schema version when adding tables. Read the current `version:` number and increment by 1.

---

## Step 3: Create Offline TypeScript Calculation Engine

Create these 4 files in `features/nec-calcs/utils/`:

### `calcVoltageDrop.ts`

```typescript
// frontend/apps/mobile/features/nec-calcs/utils/calcVoltageDrop.ts
/**
 * NEC 210.19(A)(1) Voltage Drop Calculator
 *
 * MIRRORS nec_service.py _calc_voltage_drop() exactly.
 * Input keys must match backend exactly — do NOT rename fields.
 */

// Copied verbatim from backend/services/nec_service.py _AWG_CIRCULAR_MILS
const AWG_CIRCULAR_MILS: Record<string, number> = {
  "14": 4110.0, "12": 6530.0, "10": 10380.0, "8": 16510.0,
  "6": 26240.0, "4": 41740.0, "3": 52620.0, "2": 66360.0,
  "1": 83690.0, "1/0": 105600.0, "2/0": 133100.0, "3/0": 167800.0,
  "4/0": 211600.0, "250": 250000.0, "300": 300000.0, "350": 350000.0,
  "400": 400000.0, "500": 500000.0,
};
const K_COPPER = 12.9;

function normalizeGauge(gauge: string): string {
  return gauge.trim().toUpperCase()
    .replace(/\s*(AWG|GAUGE|GA\.?|#)/g, "").trim();
}

function round(val: number, decimals: number): number {
  return Math.round(val * 10 ** decimals) / 10 ** decimals;
}

export interface VoltageDropInputs {
  amperage: number;
  distance_feet: number;
  wire_gauge: string;
  voltage?: number;   // default 120
  phase?: number;     // default 1
}

export interface VoltageDropResult {
  calc_type: "voltage_drop";
  result_value: number;
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
  const { amperage, distance_feet, wire_gauge, voltage = 120, phase = 1 } = inputs;
  if (amperage <= 0) throw new Error("amperage must be > 0");
  if (distance_feet <= 0) throw new Error("distance_feet must be > 0");
  if (!wire_gauge) throw new Error("wire_gauge is required");

  const normalized = normalizeGauge(wire_gauge);
  const circularMils = AWG_CIRCULAR_MILS[normalized];
  if (!circularMils) {
    throw new Error(`Unknown wire gauge: ${wire_gauge}. Use a standard AWG gauge.`);
  }

  const multiplier = phase === 3 ? 1.732 : 2.0;
  const voltageDrop = (multiplier * K_COPPER * amperage * distance_feet) / circularMils;
  const voltageDropPct = (voltageDrop / voltage) * 100;
  const isCompliant = voltageDropPct <= 3.0;

  return {
    calc_type: "voltage_drop",
    result_value: round(voltageDrop, 4),
    is_compliant: isCompliant,
    nec_article: "NEC 210.19(A)(1)",
    nec_citation: "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
    voltage_drop: round(voltageDrop, 4),
    voltage_drop_pct: round(voltageDropPct, 4),
    wire_gauge,
    wire_gauge_normalized: normalized,
    amperage,
    distance_feet,
    voltage,
    phase,
  };
}
```

### `calcConduitFill.ts`

Mirror `_calc_conduit_fill()` from `nec_service.py`. Copy the conduit area tables (`_CONDUIT_AREA_SQ_IN`) and wire area tables (`_AWG_WIRE_AREA_SQ_IN`) verbatim. Follow the same input key names: `conduit_trade_size`, `conduit_type`, `wire_gauge`, `num_conductors`.

### `calcAmpacity.ts`

Mirror `_calc_ampacity()` from `nec_service.py`. Copy all ampacity tables (`_COPPER_AMPACITY_75C`, `_COPPER_AMPACITY_90C`, `_BUNDLING_ADJUSTMENT_FACTORS`). Input keys: `wire_material`, `wire_gauge`, `temp_rating_c`, `conductor_count`, `ambient_temp_c`.

### `index.ts` (router)

```typescript
// frontend/apps/mobile/features/nec-calcs/utils/index.ts
import { calcVoltageDrop, type VoltageDropResult } from "./calcVoltageDrop";
import { calcConduitFill, type ConduitFillResult } from "./calcConduitFill";
import { calcAmpacity, type AmpacityResult } from "./calcAmpacity";

export type NecOfflineResult = VoltageDropResult | ConduitFillResult | AmpacityResult;

export function calculateOffline(
  calcType: string,
  inputs: Record<string, unknown>,
): NecOfflineResult {
  switch (calcType) {
    case "voltage_drop":
      return calcVoltageDrop(inputs as VoltageDropInputs);
    case "conduit_fill":
      return calcConduitFill(inputs as ConduitFillInputs);
    case "ampacity":
      return calcAmpacity(inputs as AmpacityInputs);
    default:
      throw new Error(`Unknown calc_type: ${calcType}`);
  }
}
```

---

## Step 4: Create `useNecCalculate` Hook (Dual-Path)

**File**: `frontend/apps/mobile/features/nec-calcs/hooks/useNecCalculate.ts`

Online/offline detection — first check `netinfo` availability:
```bash
grep "netinfo" frontend/apps/mobile/package.json
```

**If `@react-native-community/netinfo` present**:
```typescript
import NetInfo from "@react-native-community/netinfo";
const state = await NetInfo.fetch();
const isOnline = state.isConnected === true && state.isInternetReachable !== false;
```

**If NOT present** (fallback):
```typescript
const isOnline = typeof navigator !== "undefined" ? (navigator.onLine ?? false) : false;
// TODO: install @react-native-community/netinfo for more reliable detection
```

The hook itself:

```typescript
import { apiClient } from "@pilot/shared-api";
import { database } from "../../../database";
import type { NecCalcLog } from "../../../database/models/NecCalcLog";
import { calculateOffline } from "../utils";

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function useNecCalculate() {
  const [result, setResult] = useState<NecOfflineResult | null>(null);
  const [isOfflineCalc, setIsOfflineCalc] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = useCallback(async (
    calcType: "voltage_drop" | "conduit_fill" | "ampacity",
    inputs: Record<string, unknown>,
  ) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    const isOnline = await checkIsOnline();

    if (isOnline) {
      try {
        const idempotencyKey = generateIdempotencyKey();
        const { data } = await apiClient.post("/api/v1/nec/calculate", {
          calc_type: calcType,
          inputs,
          idempotency_key: idempotencyKey,
        });
        setResult(data.result);
        setIsOfflineCalc(false);
      } catch (err) {
        // API failed — fallback to offline engine
        await runOffline(calcType, inputs);
      }
    } else {
      await runOffline(calcType, inputs);
    }

    setIsLoading(false);
  }, []);

  const runOffline = async (
    calcType: string,
    inputs: Record<string, unknown>,
  ) => {
    try {
      const offlineResult = calculateOffline(calcType, inputs);
      const idempotencyKey = generateIdempotencyKey();

      await database.write(async () => {
        return database.get<NecCalcLog>("nec_calc_logs").create((record) => {
          record.calcType = calcType;
          record.inputsJson = inputs;
          record.resultJson = offlineResult as Record<string, unknown>;
          record.necGuideVersion = "2023";
          record.isOfflineCalc = true;
          record.idempotencyKey = idempotencyKey;
          record.localSyncStatus = "pending";
          record.syncError = null;
          record.retryCount = 0;
        });
      });

      setResult(offlineResult);
      setIsOfflineCalc(true);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Calculation failed";
      setError(msg);
    }
  };

  return { result, isOfflineCalc, isLoading, error, calculate };
}
```

---

## Step 5: Create `useNecCalcLogs` Hook

**File**: `frontend/apps/mobile/features/nec-calcs/hooks/useNecCalcLogs.ts`

```typescript
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

---

## Step 6: Create MSW NEC Handlers

**File**: `frontend/apps/mobile/mocks/handlers/necHandlers.ts`

```typescript
// GET /api/v1/nec/calc-logs — return 2 saved calc fixtures
// POST /api/v1/nec/calculate — return NecCalculateResponse fixture
//   { log_id, calc_type, result: { ... voltage drop result ... }, nec_guide_version, nec_citation }
```

Register in `mocks/handlers/index.ts`:
```typescript
import { necHandlers } from "./necHandlers";
// Add: // MOB-B4: NEC calculator endpoints
// Add: ...necHandlers
```

---

## Step 7: Create Shared UI Components

### `OfflineBanner.tsx`

```typescript
// frontend/apps/mobile/features/nec-calcs/components/OfflineBanner.tsx

export function OfflineBanner({ testID = "offline-banner" }: { testID?: string }) {
  return (
    <View style={styles.banner} testID={testID}>
      <Text style={styles.text}>
        ⚠️  Offline — using NEC 2023 code formulas
      </Text>
      <Text style={styles.subtext}>
        Result saved locally and will sync when online
      </Text>
    </View>
  );
}
// Styles: backgroundColor: colors.alert[50], border: colors.alert[200]
```

### `CalcResultDisplay.tsx`

```typescript
// frontend/apps/mobile/features/nec-calcs/components/CalcResultDisplay.tsx

export function CalcResultDisplay({ result, testID }: { result: NecOfflineResult; testID?: string }) {
  const isPass = result.is_compliant;
  return (
    <View style={styles.container} testID={testID ?? "calc-result-display"}>
      <View style={[styles.badge, isPass ? styles.passBadge : styles.failBadge]}>
        <Text style={[styles.badgeText, isPass ? styles.passText : styles.failText]}>
          {isPass ? "✓ PASS" : "✗ FAIL"}
        </Text>
      </View>
      <Text style={styles.primaryValue}>
        {formatResultValue(result)}
      </Text>
      <Text style={styles.citation}>{result.nec_citation}</Text>
    </View>
  );
}

function formatResultValue(result: NecOfflineResult): string {
  switch (result.calc_type) {
    case "voltage_drop":
      return `Voltage Drop: ${result.result_value.toFixed(2)} V (${(result as VoltageDropResult).voltage_drop_pct.toFixed(2)}%)`;
    case "conduit_fill":
      return `Fill: ${result.result_value.toFixed(1)}%`;
    case "ampacity":
      return `Adjusted Ampacity: ${result.result_value.toFixed(1)} A`;
    default:
      return `Result: ${result.result_value}`;
  }
}
```

---

## Step 8: Create `CalcsMenuScreen`

**File**: `frontend/apps/mobile/features/nec-calcs/components/CalcsMenuScreen.tsx`

```typescript
import { router } from "expo-router";

const MENU_ITEMS = [
  { icon: "⚡", label: "Voltage Drop Calculator", route: "/(tabs)/calcs/voltage-drop", testID: "menu-voltage-drop" },
  { icon: "📐", label: "Conduit Fill Calculator", route: "/(tabs)/calcs/conduit-fill", testID: "menu-conduit-fill" },
  { icon: "🔌", label: "Ampacity Calculator", route: "/(tabs)/calcs/ampacity", testID: "menu-ampacity" },
  { icon: "🕐", label: "Saved Calculations", route: "/(tabs)/calcs/saved-calcs", testID: "menu-saved-calcs" },
] as const;

export function CalcsMenuScreen() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <Text style={styles.title}>Calcs</Text>
      {MENU_ITEMS.map(({ icon, label, route, testID }) => (
        <Pressable
          key={route}
          onPress={() => router.push(route as any)}
          style={styles.menuRow}
          testID={testID}
          accessibilityRole="button"
        >
          <Text style={styles.menuIcon}>{icon}</Text>
          <Text style={styles.menuLabel}>{label}</Text>
          <Text style={styles.chevron}>›</Text>
        </Pressable>
      ))}
      {/* NEC Reference — disabled for MVP */}
      <View style={[styles.menuRow, styles.disabled]} testID="menu-nec-reference">
        <Text style={styles.menuIcon}>📚</Text>
        <Text style={[styles.menuLabel, styles.disabledText]}>NEC 2023 Reference</Text>
        <Text style={styles.comingSoon}>Coming soon</Text>
      </View>
    </SafeAreaView>
  );
}
```

---

## Step 9: Create Calculator Screens

### Voltage Drop Screen

**File**: `frontend/apps/mobile/features/nec-calcs/components/VoltageDrop/VoltageDropScreen.tsx`

Form fields:
- **Amps (A)**: `TextInput`, numeric keyboard, required
- **Distance (ft)**: `TextInput`, numeric keyboard, required
- **Wire Gauge**: Picker — options: `["14", "12", "10", "8", "6", "4", "3", "2", "1", "1/0", "2/0", "3/0", "4/0", "250", "300", "350", "400", "500"]` shown as "14 AWG" etc.
- **Voltage (V)**: `TextInput`, default "120"
- **Phase**: Radio buttons — "Single-Phase" (1) | "Three-Phase" (3)
- **[Calculate]** button — calls `calculate("voltage_drop", { amperage, distance_feet, wire_gauge, voltage, phase })`
- Result: `<OfflineBanner>` (if `isOfflineCalc`), `<CalcResultDisplay>`

Header: `← Calcs   ⚡ Voltage Drop`

### Conduit Fill Screen

**File**: `frontend/apps/mobile/features/nec-calcs/components/ConduitFill/ConduitFillScreen.tsx`

Form fields:
- **Conduit Type**: Picker — `["EMT", "RMC", "PVC40"]`
- **Conduit Size**: Picker — `["1/2", "3/4", "1", "1-1/4", "1-1/2", "2", "2-1/2", "3", "3-1/2", "4"]`
- **Wire Gauge**: Picker (same list as voltage drop)
- **Number of Conductors**: `TextInput`, numeric, required
- **[Calculate]** button — calls `calculate("conduit_fill", { conduit_trade_size, conduit_type, wire_gauge, num_conductors })`

### Ampacity Screen

**File**: `frontend/apps/mobile/features/nec-calcs/components/Ampacity/AmpacityScreen.tsx`

Form fields:
- **Wire Material**: Radio — "Copper" | "Aluminum" (default Copper; note: design doc §F.3 copper tables implemented — aluminum requires additional tables)
- **Wire Gauge**: Picker (same list)
- **Temperature Rating**: Picker — `["60", "75", "90"]` shown as "60°C", "75°C", "90°C"
- **Conductors in Bundle**: `TextInput`, numeric, default "3"
- **Ambient Temp (°C)**: `TextInput`, numeric, default "30"
- **[Calculate]** button — calls `calculate("ampacity", { wire_material, wire_gauge, temp_rating_c, conductor_count, ambient_temp_c })`

> **Aluminum tables**: `nec_service.py` implements aluminum ampacity. If aluminum tables are complex to port, display copper only for MVP with `// TODO: add aluminum when tables verified` note.

### Saved Calculations Screen

**File**: `frontend/apps/mobile/features/nec-calcs/components/SavedCalcsScreen.tsx`

```typescript
export function SavedCalcsScreen() {
  const { data: logs, isLoading, isError, refetch } = useNecCalcLogs();

  if (isLoading) return <ActivityIndicator />;
  if (isError) return <ErrorState onRetry={refetch} />;

  return (
    <FlatList
      data={logs ?? []}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => <SavedCalcRow log={item} />}
      ListEmptyComponent={<Text>No saved calculations yet</Text>}
      refreshControl={<RefreshControl onRefresh={refetch} />}
    />
  );
}
```

Each `SavedCalcRow` shows: calc type badge, `result_json.result_value` formatted, pass/fail dot, offline badge if `is_offline_calc`, relative timestamp.

---

## Step 10: Replace `calcs.tsx` Stub

**File**: `frontend/apps/mobile/app/(tabs)/calcs.tsx`

Read first (confirm still 10-line stub), then replace:

```typescript
import { CalcsMenuScreen } from "@/features/nec-calcs/components/CalcsMenuScreen";

export default function CalcsTab() {
  return <CalcsMenuScreen />;
}
```

---

## Step 11: Create Route Files

**`app/(tabs)/calcs/voltage-drop.tsx`**:
```typescript
import { VoltageDropScreen } from "@/features/nec-calcs/components/VoltageDrop/VoltageDropScreen";
export default function VoltageDropRoute() { return <VoltageDropScreen />; }
```

Repeat for `conduit-fill.tsx`, `ampacity.tsx`, `saved-calcs.tsx`.

---

## Step 12: Update `_layout.tsx`

Read the file first. Add 4 suppressions:
```typescript
{/* MOB-B4: Calcs sub-screens — suppress from tab bar */}
<Tabs.Screen name="calcs/voltage-drop" options={{ href: null }} />
<Tabs.Screen name="calcs/conduit-fill" options={{ href: null }} />
<Tabs.Screen name="calcs/ampacity" options={{ href: null }} />
<Tabs.Screen name="calcs/saved-calcs" options={{ href: null }} />
```

---

## Tests

### Unit Tests — Pure Calculation Functions

**`calcVoltageDrop.test.ts`**:
- 12 AWG, 100ft, 20A, 120V, single-phase → `voltage_drop_pct ≈ 6.59%`, `is_compliant=false`
- Phase=3 → √3 (1.732) multiplier applied (vs 2.0 for single-phase)
- 12 AWG, 50ft, 10A, 120V → `is_compliant=true` (< 3%)
- Unknown gauge "7 AWG" → `Error`

**`calcConduitFill.test.ts`**:
- EMT 3/4", 3× #12: `3 × 0.0133 / 0.533 × 100 ≈ 7.49%`, `is_compliant=true`
- 3+ conductors: >40% fill → `is_compliant=false`
- 2 conductors: >31% fill → `is_compliant=false`
- 1 conductor: >53% fill → `is_compliant=false`

**`calcAmpacity.test.ts`**:
- #12 copper, 75°C, 30°C ambient, 3 conductors → base ampacity 25A, correction factor 1.0, bundling 1.0 → adjusted 25A
- 4 conductors → bundling factor 0.80 applied
- 90°C rating → uses `_COPPER_AMPACITY_90C` table (30A for #12)

**`index.test.ts`**:
- `calculateOffline("voltage_drop", ...)` → calls `calcVoltageDrop`
- `calculateOffline("unknown", ...)` → throws Error

### Unit Tests — Hook

**`useNecCalculate.test.ts`**:
- Online: `POST /api/v1/nec/calculate` called via MSW; `isOfflineCalc=false`
- Offline (mocked `navigator.onLine=false`): TypeScript engine used; `isOfflineCalc=true`
- Offline: WatermelonDB `nec_calc_logs` record created with `localSyncStatus="pending"`
- API 500 error → fallback to offline engine (not an error state)

### Integration Tests (`__tests__/batch_mob_b4/`)

**`calcs-tab.integration.test.tsx`**:
- No "Calcs" centered text in rendered output (stub removed)
- 4 active menu rows (VD, CF, Amp, Saved) + 1 disabled (NEC Reference)
- Tap "Voltage Drop Calculator" → `router.push` to `calcs/voltage-drop`
- Tap "Saved Calculations" → `router.push` to `calcs/saved-calcs`

**`voltage-drop.integration.test.tsx`**:
- Fill form → submit → MSW called → result displayed with pass/fail
- `OfflineBanner` shown when `isOfflineCalc=true`
- `CalcResultDisplay` shows "✓ PASS" when `is_compliant=true`
- `CalcResultDisplay` shows "✗ FAIL" when `is_compliant=false`

**`saved-calcs.integration.test.tsx`**:
- MSW returns 2 logs → 2 rows rendered
- Pull-to-refresh → `refetch` called
- Empty state shown when 0 logs

### Regression Tests

- `_layout.tsx` existing suppressions still intact (`jobs/[jobId]/index`, `customers/[id]/index`, comms)
- All existing mobile test suites pass (WatermelonDB schema version increment must not break existing tests)

---

## Final Verification

```bash
cd <repo>/frontend
pnpm --filter mobile check-types && \
pnpm --filter mobile lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter mobile test 2>&1 | tail -10 && \
echo "=== MOB-B4 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B4

Update `pilot-app-beta-fixes-v2-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] MOB-B0 confirmed complete — `POST /api/v1/nec/calculate` in `openapi_schema_map.md`
- [ ] `backend/services/nec_service.py` read fully — all lookup tables + input keys confirmed
- [ ] `database/schema.ts` read before modification
- [ ] `@react-native-community/netinfo` availability checked — documented fallback if absent
- [ ] `NecCalcLog` WatermelonDB model created (`database/models/NecCalcLog.ts`)
- [ ] `nec_calc_logs` table added to `database/schema.ts` with incremented schema version
- [ ] `calcVoltageDrop.ts` — mirrors `nec_service.py _calc_voltage_drop()` exactly; same input keys; same AWG table
- [ ] `calcConduitFill.ts` — mirrors `nec_service.py _calc_conduit_fill()` exactly; same conduit/wire tables
- [ ] `calcAmpacity.ts` — mirrors `nec_service.py _calc_ampacity()` exactly; same ampacity/bundling tables
- [ ] `calculateOffline()` router in `nec-calcs/utils/index.ts` routes to correct function
- [ ] `useNecCalculate` dual-path: online → API; offline → TypeScript engine; API failure → offline fallback
- [ ] Offline path: saves to WatermelonDB with `localSyncStatus="pending"`
- [ ] `useNecCalcLogs`: calls `GET /api/v1/nec/calc-logs`
- [ ] `necHandlers.ts` MSW fixtures created and registered
- [ ] `OfflineBanner` renders with correct "⚠️ Offline" copy — no "verify online" language
- [ ] `CalcResultDisplay` shows "✓ PASS" (green) and "✗ FAIL" (red) correctly
- [ ] `CalcsMenuScreen` has 5 rows — 4 navigable, 1 disabled "Coming soon"
- [ ] `VoltageDropScreen` — form with picker for gauge/phase; calls `calculate("voltage_drop", ...)`
- [ ] `ConduitFillScreen` — form with pickers for conduit type/size/gauge; calls `calculate("conduit_fill", ...)`
- [ ] `AmpacityScreen` — form with pickers; calls `calculate("ampacity", ...)`
- [ ] `SavedCalcsScreen` — lists logs from API; empty state; pull-to-refresh
- [ ] `calcs.tsx` stub replaced — no longer shows centered "Calcs" text
- [ ] 4 route files created (`calcs/voltage-drop.tsx`, `conduit-fill.tsx`, `ampacity.tsx`, `saved-calcs.tsx`)
- [ ] `_layout.tsx` updated — 4 calcs sub-screen suppressions added
- [ ] Unit tests for all 3 offline calc functions pass (all per §J.1 in design doc)
- [ ] `useNecCalculate` hook tests pass (online + offline paths)
- [ ] Integration tests pass (menu + VD calculator + saved calcs)
- [ ] Regression tests pass — existing layout suppressions intact, no WatermelonDB schema errors
- [ ] Zero TypeScript errors (`pnpm --filter mobile check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing mobile test suite
- [ ] Full verification command passes (`=== MOB-B4 FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented in impl plan tracker
- [ ] Summary of work accomplished added to impl plan §9 as new sub-section after MOB-B4 row
