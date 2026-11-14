/**
 * NotificationBanner — Mobile variant
 *
 * Location: packages/ui/src/notification-banner/mobile/NotificationBanner.tsx
 * All typography and spacing uses tokens from @pilot/ui/tokens.
 */

import React, { useEffect } from "react";
import { View, Text, Pressable } from "react-native";
import { mobileFontSizes, fontWeights, spacing, radii } from "../../tokens";
import type { NotificationBannerMobileProps } from "../types";
import { AUTO_DISMISS_MS } from "../types";

/**
 * NotificationBanner (mobile)
 */
export function NotificationBanner({
  notification,
  onDismiss,
  onNavigate,
}: NotificationBannerMobileProps) {
  const { id, severity, title, detail, deepLinkTarget, dismissAfterMs } =
    notification;

  const autoDismissMs =
    dismissAfterMs !== undefined ? dismissAfterMs : AUTO_DISMISS_MS[severity];

  useEffect(() => {
    if (autoDismissMs === null) return;
    const timer = setTimeout(() => {
      onDismiss(id);
    }, autoDismissMs);
    return () => clearTimeout(timer);
  }, [id, autoDismissMs, onDismiss]);

  function handlePress() {
    if (deepLinkTarget && onNavigate) {
      onNavigate(deepLinkTarget);
    }
  }

  return (
    <Pressable
      testID={`notification-banner-${id}`}
      accessibilityRole="alert"
      accessibilityLabel={`${title}${detail ? `. ${detail}` : ""}`}
      accessibilityLiveRegion={
        severity === "error" || severity === "critical" ? "assertive" : "polite"
      }
      onPress={deepLinkTarget ? handlePress : undefined}
      style={({ pressed }) => ({
        flexDirection: "row",
        alignItems: "flex-start",
        borderRadius: radii.md,
        padding: spacing[3],
        gap: spacing[2],
        opacity: pressed ? 0.9 : 1,
      })}
    >
      <View style={{ flex: 1, gap: spacing[1] }}>
        <Text
          style={{
            fontSize: mobileFontSizes.body,
            fontWeight: String(fontWeights.medium) as "500",
          }}
        >
          {title}
        </Text>
        {detail && (
          <Text style={{ fontSize: mobileFontSizes.caption }}>{detail}</Text>
        )}
      </View>

      {/* Dismiss button */}
      <Pressable
        onPress={() => onDismiss(id)}
        testID={`notification-banner-${id}-dismiss`}
        accessibilityRole="button"
        accessibilityLabel={`Dismiss: ${title}`}
        hitSlop={{
          top: spacing[2],
          bottom: spacing[2],
          left: spacing[2],
          right: spacing[2],
        }}
      >
        <Text
          style={{
            fontSize: mobileFontSizes.bodyLg,
            lineHeight: mobileFontSizes.bodyLg,
          }}
        >
          ×
        </Text>
      </Pressable>
    </Pressable>
  );
}
