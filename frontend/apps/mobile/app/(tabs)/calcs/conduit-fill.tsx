/**
 * Calcs / Conduit Fill — Route File
 *
 * Location: apps/mobile/app/(tabs)/calcs/conduit-fill.tsx
 *
 * Suppressed from tab bar in _layout.tsx (href: null).
 * Navigated to from CalcsMenuScreen via router.push.
 *
 * Per batch-mob-b4-design.md §B.3.
 */

import { ConduitFillScreen } from "@/features/nec-calcs/components/ConduitFill/ConduitFillScreen";

export default function ConduitFillRoute() {
  return <ConduitFillScreen />;
}
