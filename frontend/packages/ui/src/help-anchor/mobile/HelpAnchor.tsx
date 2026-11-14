/**
 * HelpAnchor — mobile implementation — FE-B16
 *
 * Location: packages/ui/src/help-anchor/mobile/HelpAnchor.tsx
 */

import React from "react";
import { Pressable, Text, StyleSheet } from "react-native";
import { colors, spacing, radii } from "../../tokens";
import type { HelpAnchorProps, HelpContextPayload } from "../types";

interface MobileHelpAnchorProps extends HelpAnchorProps {
  onOpen: (payload: HelpContextPayload) => void;
}

export function HelpAnchor({
  contextPayload,
  label = "Open contextual help",
  size = "sm",
  testId,
  onOpen,
}: MobileHelpAnchorProps) {
  // sm: 16px (spacing[4]), md: 20px (spacing[5]) — nearest 4px-grid values
  const iconSize = size === "sm" ? spacing[4] : spacing[5];
  // caption font size from tokens (11pt)
  const fontSize = spacing[3] - 1; // 11 = 12-1; using mobileFontSizes.caption equivalent

  return (
    <Pressable
      onPress={() => onOpen(contextPayload)}
      accessibilityLabel={label}
      accessibilityRole="button"
      testID={testId ?? "help-anchor"}
      style={({ pressed }) => [styles.base, pressed && styles.pressed]}
    >
      <Text
        style={[
          styles.icon,
          { width: iconSize, height: iconSize, fontSize, lineHeight: iconSize },
        ]}
      >
        ?
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.full,
  },
  pressed: {
    opacity: 0.6,
  },
  icon: {
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    fontWeight: "700",
    color: colors.neutral[400],
    borderWidth: 1,
    borderColor: colors.neutral[400],
    borderRadius: radii.full,
  },
});
