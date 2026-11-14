/**
 * NEC Offline Calculation Engine — Router
 *
 * Location: apps/mobile/features/nec-calcs/utils/index.ts
 *
 * Routes offline calculation requests to the correct pure function.
 * Used by useNecCalculate when device is offline or API call fails.
 *
 * Per batch-mob-b4-design.md §F.3.
 */

import { calcVoltageDrop } from "./calcVoltageDrop";
import { calcConduitFill } from "./calcConduitFill";
import { calcAmpacity } from "./calcAmpacity";

export type { VoltageDropInputs, VoltageDropResult } from "./calcVoltageDrop";
export type { ConduitFillInputs, ConduitFillResult } from "./calcConduitFill";
export type { AmpacityInputs, AmpacityResult } from "./calcAmpacity";

export { calcVoltageDrop } from "./calcVoltageDrop";
export { calcConduitFill } from "./calcConduitFill";
export { calcAmpacity } from "./calcAmpacity";

/** Union of all possible offline calc results */
export type NecOfflineResult =
  | ReturnType<typeof calcVoltageDrop>
  | ReturnType<typeof calcConduitFill>
  | ReturnType<typeof calcAmpacity>;

/**
 * Route offline calculation to the correct TypeScript engine function.
 *
 * @param calcType - "voltage_drop" | "conduit_fill" | "ampacity"
 * @param inputs   - Calculation inputs matching backend key names exactly
 * @returns NecOfflineResult with result_value, is_compliant, nec_citation
 * @throws Error if calcType is unknown or inputs are invalid
 */
export function calculateOffline(
  calcType: string,
  inputs: Record<string, unknown>,
): NecOfflineResult {
  switch (calcType) {
    case "voltage_drop":
      return calcVoltageDrop(
        inputs as unknown as Parameters<typeof calcVoltageDrop>[0],
      );
    case "conduit_fill":
      return calcConduitFill(
        inputs as unknown as Parameters<typeof calcConduitFill>[0],
      );
    case "ampacity":
      return calcAmpacity(
        inputs as unknown as Parameters<typeof calcAmpacity>[0],
      );
    default:
      throw new Error(
        `Unknown calc_type: ${calcType}. Valid values: 'voltage_drop', 'conduit_fill', 'ampacity'`,
      );
  }
}
