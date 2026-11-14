/**
 * LoadingState — Mobile variant
 *
 * Location: packages/ui/src/states/mobile/LoadingState.tsx
 * All typography and spacing uses tokens from @pilot/ui/tokens.
 */

import React, { useEffect, useRef } from "react";
import { View, Text, Animated, ActivityIndicator } from "react-native";
import { mobileFontSizes, spacing } from "../../tokens";
import type { LoadingStateProps } from "../types";

function SkeletonRow({ index }: { index: number }) {
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 800,
          delay: index * 100,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.3,
          duration: 800,
          useNativeDriver: true,
        }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [opacity, index]);

  const WIDTHS = ["100%", "80%", "75%", "67%", "83%", "100%"] as const;
  const widthValue = WIDTHS[index % WIDTHS.length] ?? "100%";

  return (
    <Animated.View
      style={{
        height: spacing[4],
        borderRadius: spacing[1],
        width: widthValue,
        opacity,
      }}
      accessibilityElementsHidden
    />
  );
}

/**
 * LoadingState (mobile)
 */
export function LoadingState({
  type,
  skeletonRows = 4,
  label = "Loading\u2026",
  children,
  testID,
}: LoadingStateProps) {
  if (type === "full-page") {
    return (
      <View
        testID={testID ?? "loading-state-full-page"}
        accessibilityLabel={label}
        style={{ flex: 1, padding: spacing[8], gap: spacing[4] }}
      >
        {Array.from({ length: skeletonRows }, (_, i) => (
          <SkeletonRow key={i} index={i} />
        ))}
      </View>
    );
  }

  if (type === "inline") {
    return (
      <View
        testID={testID ?? "loading-state-inline"}
        accessibilityLabel={label}
        accessibilityLiveRegion="polite"
        style={{ flexDirection: "row", alignItems: "center", gap: spacing[2] }}
      >
        <ActivityIndicator size="small" accessibilityLabel={label} />
        <Text style={{ fontSize: mobileFontSizes.body }}>{label}</Text>
      </View>
    );
  }

  // optimistic
  return (
    <View
      testID={testID ?? "loading-state-optimistic"}
      style={{ opacity: 0.7 }}
    >
      {children}
    </View>
  );
}
