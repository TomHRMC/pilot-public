/**
 * FirstTimeUserState — Mobile variant
 *
 * Location: packages/ui/src/states/mobile/FirstTimeUserState.tsx
 * All typography and spacing uses tokens from @pilot/ui/tokens.
 *
 * Mobile only supports: dashboard | schedule | customers.
 * Other surfaces return null silently.
 */

import React from "react";
import { View, Text, Pressable } from "react-native";
import { mobileFontSizes, fontWeights, spacing, radii } from "../../tokens";
import type { FirstTimeUserStateProps } from "../types";
import { FTU_DEFAULTS, MOBILE_SUPPORTED_FTU_TYPES } from "../types";

/**
 * FirstTimeUserState (mobile)
 */
export function FirstTimeUserState({
  type,
  headingText,
  bodyText,
  ctaLabel,
  onCta,
  secondaryCtaLabel,
  onSecondaryCta,
  testID,
}: FirstTimeUserStateProps) {
  if (!MOBILE_SUPPORTED_FTU_TYPES.includes(type)) {
    return null;
  }

  const defaults = FTU_DEFAULTS[type];
  const resolvedHeading = headingText ?? defaults.heading;
  const resolvedBody = bodyText ?? defaults.body;
  const resolvedCtaLabel = ctaLabel ?? defaults.ctaLabel;

  return (
    <View
      testID={testID ?? `ftu-state-${type}`}
      style={{
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
        padding: spacing[8],
        gap: spacing[6],
      }}
    >
      {/* Icon placeholder */}
      <View
        style={{
          width: spacing[16],
          height: spacing[16],
          borderRadius: spacing[8],
          alignItems: "center",
          justifyContent: "center",
        }}
        accessibilityElementsHidden
      />

      <View style={{ alignItems: "center", gap: spacing[3], maxWidth: 280 }}>
        <Text
          style={{
            fontSize: mobileFontSizes.h2,
            fontWeight: String(fontWeights.medium) as "500",
            textAlign: "center",
          }}
          accessibilityRole="header"
        >
          {resolvedHeading}
        </Text>
        <Text style={{ fontSize: mobileFontSizes.body, textAlign: "center" }}>
          {resolvedBody}
        </Text>
      </View>

      <View style={{ alignItems: "center", gap: spacing[3] }}>
        <Pressable
          onPress={onCta}
          testID={`${testID ?? `ftu-state-${type}`}-cta`}
          accessibilityRole="button"
          accessibilityLabel={resolvedCtaLabel}
          style={({ pressed }) => ({
            paddingHorizontal: spacing[6],
            paddingVertical: spacing[3],
            borderRadius: radii.md,
            opacity: pressed ? 0.8 : 1,
          })}
        >
          <Text
            style={{
              fontSize: mobileFontSizes.body,
              fontWeight: String(fontWeights.medium) as "500",
            }}
          >
            {resolvedCtaLabel}
          </Text>
        </Pressable>

        {secondaryCtaLabel && (
          <Pressable
            onPress={onSecondaryCta}
            testID={`${testID ?? `ftu-state-${type}`}-secondary-cta`}
            accessibilityRole="button"
            accessibilityLabel={secondaryCtaLabel}
          >
            <Text
              style={{
                fontSize: mobileFontSizes.body,
                textDecorationLine: "underline",
              }}
            >
              {secondaryCtaLabel}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}
