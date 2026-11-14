/**
 * EmptyState — Mobile variant
 *
 * Location: packages/ui/src/states/mobile/EmptyState.tsx
 * Rendered by: React Native primitives (View, Text, Pressable)
 *
 * All typography uses mobileFontSizes / fontWeights tokens from @pilot/ui/tokens.
 * All spacing uses spacing tokens from @pilot/ui/tokens.
 * No hardcoded design values.
 */

import React from "react";
import { View, Text, Pressable } from "react-native";
import { mobileFontSizes, fontWeights, spacing, radii } from "../../tokens";
import type { EmptyStateProps } from "../types";
import { EMPTY_STATE_DEFAULTS } from "../types";

/**
 * EmptyState (mobile)
 *
 * @example
 * <EmptyState type="no-data" ctaLabel="Create your first quote" onCta={handleCreate} />
 */
export function EmptyState({
  type,
  title,
  description,
  ctaLabel,
  onCta,
  secondaryCtaLabel,
  onSecondaryCta,
  testID,
}: EmptyStateProps) {
  const defaults = EMPTY_STATE_DEFAULTS[type];
  const resolvedTitle = title ?? defaults.title;
  const resolvedDescription = description ?? defaults.description;

  return (
    <View
      testID={testID ?? `empty-state-${type}`}
      accessibilityRole="none"
      style={{
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
        padding: spacing[8],
      }}
    >
      <View style={{ alignItems: "center", gap: spacing[2] }}>
        <Text
          style={{
            fontSize: mobileFontSizes.h2,
            fontWeight: String(fontWeights.medium) as "500",
            textAlign: "center",
          }}
          accessibilityRole="header"
        >
          {resolvedTitle}
        </Text>
        <Text
          style={{
            fontSize: mobileFontSizes.body,
            textAlign: "center",
            maxWidth: 280,
          }}
        >
          {resolvedDescription}
        </Text>
      </View>

      {(onCta ?? ctaLabel) && (
        <View
          style={{
            marginTop: spacing[4],
            alignItems: "center",
            gap: spacing[2],
          }}
        >
          <Pressable
            onPress={onCta}
            testID={`${testID ?? `empty-state-${type}`}-cta`}
            accessibilityRole="button"
            accessibilityLabel={ctaLabel}
            style={({ pressed }) => ({
              paddingHorizontal: spacing[4],
              paddingVertical: spacing[2],
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
              {ctaLabel}
            </Text>
          </Pressable>

          {secondaryCtaLabel && (
            <Pressable
              onPress={onSecondaryCta}
              testID={`${testID ?? `empty-state-${type}`}-secondary-cta`}
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
      )}
    </View>
  );
}
