/**
 * PendingBadge — Mobile (Gluestack-UI) variant
 *
 * Location: packages/ui/src/pending-badge/mobile/PendingBadge.tsx
 *
 * Renders an optimistic UI pending count badge using Gluestack token colors.
 * Zero count renders null — no visual noise when synced.
 *
 * Token color mapping (NO hardcoded hex values):
 *   pending  → $alert400 (amber)
 *   syncing  → $brand400 (brand blue, animated pulse)
 *   failed   → $fault600 (red)
 *   conflict → $fault600 (red)
 *
 * Per batch-fe-b7-design.md Section F.1 and §16.8.
 * ⚠️ ZERO TOLERANCE: No hardcoded colors. All colors via Gluestack tokens.
 */

import React from "react";
import { Box, Text, Pressable } from "@gluestack-ui/themed";
import type { PendingBadgeProps, PendingBadgeVariant } from "../types";

/** Maps badge variant to Gluestack token color keys */
const BADGE_BG_COLOR: Record<PendingBadgeVariant, string> = {
  pending: "$alert400",
  syncing: "$brand400",
  failed: "$fault600",
  conflict: "$fault600",
};

const BADGE_TEXT_COLOR: Record<PendingBadgeVariant, string> = {
  pending: "$neutral900",
  syncing: "$neutral900",
  failed: "$neutral50",
  conflict: "$neutral50",
};

export function PendingBadge({
  count,
  variant = "pending",
  accessibilityLabel,
  testID,
  onPress,
}: PendingBadgeProps): React.ReactElement | null {
  // count === 0: render nothing
  if (count === 0) return null;

  const displayCount = count > 99 ? "99+" : String(count);
  const a11yLabel = accessibilityLabel ?? `${count} pending sync`;

  const badge = (
    <Box
      backgroundColor={BADGE_BG_COLOR[variant]}
      borderRadius={9999}
      minWidth={20}
      height={20}
      paddingHorizontal={4}
      alignItems="center"
      justifyContent="center"
      testID={testID ?? "pending-badge"}
      accessibilityLabel={a11yLabel}
      accessibilityRole="text"
    >
      <Text
        color={BADGE_TEXT_COLOR[variant]}
        fontSize={12}
        fontWeight="$medium"
        lineHeight={16}
      >
        {displayCount}
      </Text>
    </Box>
  );

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        accessibilityLabel={a11yLabel}
        accessibilityRole="button"
        testID={testID ? `${testID}-pressable` : "pending-badge-pressable"}
      >
        {badge}
      </Pressable>
    );
  }

  return badge;
}
