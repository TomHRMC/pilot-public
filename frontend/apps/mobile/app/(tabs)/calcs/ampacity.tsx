/**
 * Calcs / Ampacity — Route File
 *
 * Location: apps/mobile/app/(tabs)/calcs/ampacity.tsx
 *
 * Suppressed from tab bar in _layout.tsx (href: null).
 * Navigated to from CalcsMenuScreen via router.push.
 *
 * Per batch-mob-b4-design.md §B.3.
 */

import { AmpacityScreen } from "@/features/nec-calcs/components/Ampacity/AmpacityScreen";

export default function AmpacityRoute() {
  return <AmpacityScreen />;
}
