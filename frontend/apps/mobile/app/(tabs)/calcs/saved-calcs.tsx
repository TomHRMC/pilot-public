/**
 * Calcs / Saved Calculations — Route File
 *
 * Location: apps/mobile/app/(tabs)/calcs/saved-calcs.tsx
 *
 * Suppressed from tab bar in _layout.tsx (href: null).
 * Navigated to from CalcsMenuScreen via router.push.
 *
 * Per batch-mob-b4-design.md §B.3.
 */

import { SavedCalcsScreen } from "@/features/nec-calcs/components/SavedCalcsScreen";

export default function SavedCalcsRoute() {
  return <SavedCalcsScreen />;
}
