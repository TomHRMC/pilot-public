/**
 * Password Reset modal screen — mobile
 *
 * Location: apps/mobile/app/(auth)/password-reset.tsx
 *
 * FE-B2: Modal presentation of the PasswordResetFlow component.
 * Presented as Stack.Screen with presentation: "modal" from (auth)/_layout.tsx.
 */

import React from "react";
import { View, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { PasswordResetFlow } from "@/features/login/components/PasswordResetFlow";
import { tokens } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";

export default function PasswordResetScreen() {
  const router = useRouter();

  const handleSuccess = () => {
    // PasswordResetFlow transitions internally to success step
  };

  const handleDismiss = () => {
    router.back();
  };

  return (
    <View style={styles.container}>
      <PasswordResetFlow onSuccess={handleSuccess} onDismiss={handleDismiss} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: lightTheme.background.secondary,
    padding: tokens.spacing[6],
  },
});
