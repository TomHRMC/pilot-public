/**
 * Login screen — mobile
 *
 * Location: apps/mobile/app/(auth)/login.tsx
 *
 * FE-B2: Full login screen for mobile using LoginForm + usePostLoginRedirect.
 */

import React from "react";
import {
  View,
  Text,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
} from "react-native";
import { LoginForm } from "@/features/login/components/LoginForm";
import { usePostLoginRedirect } from "@/hooks/usePostLoginRedirect";
import type { PilotRole } from "@pilot/ui/auth";
import { tokens, fontWeights } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";

// Mock mode is ONLY active on web (localhost:8081 dev view).
// Native (Expo Go / device) must always use real Cognito authentication
// even when EXPO_PUBLIC_USE_MOCK_AUTH=true in .env.
const isMockMode =
  Platform.OS === "web" && process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

export default function LoginScreen() {
  const { navigateForRole } = usePostLoginRedirect();

  function handleSuccess(role: PilotRole) {
    navigateForRole(role);
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.flex}
    >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Text style={styles.title}>Pilot for Trades</Text>
          <Text style={styles.subtitle}>Sign in to your account</Text>
        </View>

        <View style={styles.formCard}>
          <LoginForm onSuccess={handleSuccess} mockMode={isMockMode} />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: tokens.colors.neutral[100],
  },
  container: {
    flexGrow: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacing[6],
    gap: tokens.spacing[6],
  },
  header: {
    alignItems: "center",
    gap: tokens.spacing[1],
  },
  title: {
    fontSize: tokens.mobileFontSizes.h1,
    lineHeight: tokens.mobileLineHeights.h1,
    fontWeight: fontWeights.medium,
    color: tokens.colors.neutral[900],
    textAlign: "center",
  },
  subtitle: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
    textAlign: "center",
  },
  formCard: {
    width: "100%",
    backgroundColor: lightTheme.background.secondary,
    borderRadius: tokens.radii.lg,
    padding: tokens.spacing[6],
  },
});
