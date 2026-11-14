/**
 * Calcs / Voltage Drop — Route File
 *
 * Location: apps/mobile/app/(tabs)/calcs/voltage-drop.tsx
 *
 * Suppressed from tab bar in _layout.tsx (href: null).
 * Navigated to from CalcsMenuScreen via router.push.
 *
 * Per batch-mob-b4-design.md §B.3.
 */

import { VoltageDropScreen } from "@/features/nec-calcs/components/VoltageDrop/VoltageDropScreen";

export default function VoltageDropRoute() {
  return <VoltageDropScreen />;
}
