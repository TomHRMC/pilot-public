/**
 * NecCalcLog — WatermelonDB model for offline NEC calculation storage
 *
 * Location: apps/mobile/database/models/NecCalcLog.ts
 *
 * Stores NEC calculation results locally when:
 *   (a) Device is offline — TypeScript offline engine used
 *   (b) API call fails — offline engine fallback used
 *
 * Records with localSyncStatus='pending' are synced to
 * POST /api/v1/nec/calc-logs on reconnect via SyncOrchestrator.
 *
 * Note: inputs_json and result_json are stored as text strings
 * and serialized/deserialized manually via JSON.parse/JSON.stringify.
 * WatermelonDB does not have a native JSONB column type.
 *
 * Per batch-mob-b4-design.md §B.2.
 */

import { field, text } from "@nozbe/watermelondb/decorators";
import { SyncableModel } from "./SyncableModel";

export class NecCalcLog extends SyncableModel {
  static table = "nec_calc_logs";

  /** One of: 'voltage_drop' | 'conduit_fill' | 'ampacity' */
  @text("calc_type") declare calcType: string;

  /** Serialized JSON of the calculation inputs — use JSON.parse() to read */
  @text("inputs_json") declare inputsJsonRaw: string;

  /** Serialized JSON of the NecCalcResult — use JSON.parse() to read */
  @text("result_json") declare resultJsonRaw: string;

  /** NEC guide version used for calculation, e.g. "2023" */
  @text("nec_guide_version") declare necGuideVersion: string;

  /** True when calculation was performed offline using TypeScript engine */
  @field("is_offline_calc") declare isOfflineCalc: boolean;

  /** Parsed inputs — convenience getter */
  get inputsJson(): Record<string, unknown> {
    try {
      return JSON.parse(this.inputsJsonRaw || "{}");
    } catch {
      return {};
    }
  }

  /** Parsed result — convenience getter */
  get resultJson(): Record<string, unknown> {
    try {
      return JSON.parse(this.resultJsonRaw || "{}");
    } catch {
      return {};
    }
  }
}
