/**
 * ErrorState — Mobile variant
 *
 * Location: packages/ui/src/states/mobile/ErrorState.tsx
 * All typography and spacing uses tokens from @pilot/ui/tokens.
 */

import React from "react";
import { View, Text, Pressable } from "react-native";
import { mobileFontSizes, fontWeights, spacing, radii } from "../../tokens";
import type { ErrorStateProps } from "../types";
import { ERROR_STATE_DEFAULTS } from "../types";

/**
 * ErrorState (mobile)
 */
export function ErrorState({
  type,
  title,
  description,
  onRetry,
  fieldErrors,
  onContactSupport,
  testID,
}: ErrorStateProps) {
  const defaults = ERROR_STATE_DEFAULTS[type];
  const resolvedTitle = title ?? defaults.title;
  const resolvedDescription = description ?? defaults.description;

  const showRetryCta = (type === "network" || type === "server") && onRetry;
  const showContactSupport = type === "server" && onContactSupport;
  const showFieldErrors =
    type === "validation" && fieldErrors && Object.keys(fieldErrors).length > 0;

  return (
    <View
      testID={testID ?? `error-state-${type}`}
      accessibilityRole="alert"
      accessibilityLiveRegion="assertive"
      style={{
        borderRadius: radii.md,
        padding: spacing[4],
        gap: spacing[2],
      }}
    >
      <View
        style={{
          flexDirection: "row",
          alignItems: "flex-start",
          gap: spacing[2],
        }}
      >
        <View style={{ flex: 1, gap: spacing[1] }}>
          <Text
            style={{
              fontSize: mobileFontSizes.body,
              fontWeight: String(fontWeights.medium) as "500",
            }}
            accessibilityRole="header"
          >
            {resolvedTitle}
          </Text>
          <Text style={{ fontSize: mobileFontSizes.body }}>
            {resolvedDescription}
          </Text>
        </View>
      </View>

      {showFieldErrors && (
        <View style={{ gap: spacing[1], paddingLeft: spacing[2] }}>
          {Object.entries(fieldErrors!).map(([field, error]) => (
            <Text key={field} style={{ fontSize: mobileFontSizes.caption }}>
              <Text
                style={{
                  fontWeight: String(fontWeights.medium) as "500",
                  textTransform: "capitalize",
                }}
              >
                {field}:
              </Text>{" "}
              {error}
            </Text>
          ))}
        </View>
      )}

      {(showRetryCta || showContactSupport) && (
        <View
          style={{
            flexDirection: "row",
            gap: spacing[3],
            paddingLeft: spacing[2],
            paddingTop: spacing[1],
          }}
        >
          {showRetryCta && (
            <Pressable
              onPress={onRetry}
              testID={`${testID ?? `error-state-${type}`}-retry`}
              accessibilityRole="button"
              accessibilityLabel="Try again"
            >
              <Text
                style={{
                  fontSize: mobileFontSizes.body,
                  textDecorationLine: "underline",
                }}
              >
                Try again
              </Text>
            </Pressable>
          )}
          {showContactSupport && (
            <Pressable
              onPress={onContactSupport}
              testID={`${testID ?? `error-state-${type}`}-contact`}
              accessibilityRole="button"
              accessibilityLabel="Contact support"
            >
              <Text
                style={{
                  fontSize: mobileFontSizes.body,
                  textDecorationLine: "underline",
                }}
              >
                Contact support
              </Text>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
}
