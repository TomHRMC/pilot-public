/**
 * useNecCalculate — Dual-Path NEC Calculation Hook
 *
 * Location: apps/mobile/features/nec-calcs/hooks/useNecCalculate.ts
 *
 * Online path:  POST /api/v1/nec/calculate via apiClient
 * Offline path: TypeScript NEC engine (mirrors nec_service.py exactly)
 * Fallback:     If API call fails (5xx, network error), falls back to offline engine
 *
 * Offline results are saved to WatermelonDB nec_calc_logs table with
 * localSyncStatus="pending" for sync on reconnect.
 *
 * Per batch-mob-b4-design.md §F.1.
 */

import { useState, useCallback } from "react";
import NetInfo from "@react-native-community/netinfo";
import { apiClient } from "@pilot/shared-api";
import { database } from "../../../database";
import { NecCalcLog } from "../../../database/models/NecCalcLog";
import { calculateOffline } from "../utils";
import type { NecOfflineResult } from "../utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface NecCalcResult {
  calc_type: string;
  result_value: number;
  is_compliant: boolean;
  nec_article: string;
  nec_citation: string;
  [key: string]: unknown;
}

interface NecCalcState {
  result: NecCalcResult | null;
  isOfflineCalc: boolean;
  isLoading: boolean;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateIdempotencyKey(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Use NetInfo for reliable online detection */
async function checkIsOnline(): Promise<boolean> {
  try {
    const state = await NetInfo.fetch();
    return state.isConnected === true && state.isInternetReachable !== false;
  } catch {
    // NetInfo unavailable — fallback to navigator.onLine
    return typeof navigator !== "undefined"
      ? (navigator.onLine ?? false)
      : false;
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useNecCalculate() {
  const [state, setState] = useState<NecCalcState>({
    result: null,
    isOfflineCalc: false,
    isLoading: false,
    error: null,
  });

  const runOffline = useCallback(
    async (
      calcType: string,
      inputs: Record<string, unknown>,
    ): Promise<void> => {
      try {
        const offlineResult: NecOfflineResult = calculateOffline(
          calcType,
          inputs,
        );
        const idempotencyKey = generateIdempotencyKey();

        await database.write(async () => {
          return database.get<NecCalcLog>("nec_calc_logs").create((record) => {
            record.calcType = calcType;
            record.inputsJsonRaw = JSON.stringify(inputs);
            record.resultJsonRaw = JSON.stringify(offlineResult);
            record.necGuideVersion = "2023";
            record.isOfflineCalc = true;
            // SyncableModel fields
            record.idempotencyKey = idempotencyKey;
            record.localSyncStatus = "pending";
            record.syncError = null;
            record.retryCount = 0;
          });
        });

        setState({
          result: offlineResult as unknown as NecCalcResult,
          isOfflineCalc: true,
          isLoading: false,
          error: null,
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Calculation failed";
        setState((s) => ({ ...s, isLoading: false, error: msg }));
      }
    },
    [],
  );

  const calculate = useCallback(
    async (
      calcType: "voltage_drop" | "conduit_fill" | "ampacity",
      inputs: Record<string, unknown>,
    ): Promise<void> => {
      setState((s) => ({ ...s, isLoading: true, error: null, result: null }));

      const isOnline = await checkIsOnline();

      if (isOnline) {
        try {
          const idempotencyKey = generateIdempotencyKey();
          const { data } = await apiClient.post<{
            log_id: string;
            calc_type: string;
            result: NecCalcResult;
            nec_guide_version: string;
            nec_citation: string;
          }>("/api/v1/nec/calculate", {
            calc_type: calcType,
            inputs,
            idempotency_key: idempotencyKey,
          });

          setState({
            result: data.result,
            isOfflineCalc: false,
            isLoading: false,
            error: null,
          });
        } catch (_apiErr) {
          // API call failed — fallback to offline engine
          await runOffline(calcType, inputs);
        }
      } else {
        // Device is offline — use TypeScript engine
        await runOffline(calcType, inputs);
      }
    },
    [runOffline],
  );

  return {
    result: state.result,
    isOfflineCalc: state.isOfflineCalc,
    isLoading: state.isLoading,
    error: state.error,
    calculate,
  };
}
