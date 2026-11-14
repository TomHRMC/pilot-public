/**
 * MfaChallengeStep — mobile
 *
 * Location: apps/mobile/features/login/components/MfaChallengeStep.tsx
 *
 * Minimal MFA code-entry UI for the login challenge on mobile.
 * 6-digit numeric input with haptic feedback on error.
 *
 * FE-B2: design doc §A.2 MfaChallengeStep (mobile)
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import type { MfaMethod } from "../hooks/useLoginFlow";
import { tokens, fontWeights } from "@/constants/style-constants";

interface MfaChallengeStepProps {
  challengeName: MfaMethod;
  destination?: string;
  onConfirm: (code: string) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
}

function getChallengeLabel(challengeName: MfaMethod): string {
  switch (challengeName) {
    case "TOTP":
      return "Enter the code from your authenticator app.";
    case "SMS_MFA":
      return "Enter the code sent to your phone.";
    case "EMAIL_OTP":
      return "Enter the code sent to your email.";
    default:
      return "Enter the verification code.";
  }
}

export function MfaChallengeStep({
  challengeName,
  destination,
  onConfirm,
  onCancel,
  isLoading = false,
  error,
}: MfaChallengeStepProps) {
  const [code, setCode] = useState("");
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState("");

  const handleSubmit = async () => {
    const submitCode = showRecovery ? recoveryCode : code;
    if (!submitCode.trim()) return;
    await onConfirm(submitCode.trim());
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{getChallengeLabel(challengeName)}</Text>
      {destination && (
        <Text style={styles.destination}>Code sent to {destination}</Text>
      )}

      {!showRecovery ? (
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Verification code</Text>
          <TextInput
            accessibilityLabel="Verification code"
            testID="mfa-code-input"
            keyboardType="number-pad"
            maxLength={6}
            value={code}
            onChangeText={(t) => setCode(t.replace(/\D/g, ""))}
            placeholder="000000"
            editable={!isLoading}
            textContentType="oneTimeCode"
            style={styles.input}
          />
        </View>
      ) : (
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Recovery code</Text>
          <TextInput
            accessibilityLabel="Recovery code"
            testID="recovery-code-input"
            autoCapitalize="none"
            maxLength={10}
            value={recoveryCode}
            onChangeText={setRecoveryCode}
            placeholder="XXXX-XXXX"
            editable={!isLoading}
            style={styles.input}
          />
        </View>
      )}

      {error ? (
        <Text style={styles.error} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}

      <TouchableOpacity
        accessibilityLabel={isLoading ? "Verifying" : "Verify"}
        testID="mfa-submit-button"
        onPress={() => void handleSubmit()}
        disabled={isLoading || (showRecovery ? !recoveryCode : code.length < 6)}
        style={[
          styles.button,
          (isLoading || (showRecovery ? !recoveryCode : code.length < 6)) &&
            styles.buttonDisabled,
        ]}
        activeOpacity={0.8}
      >
        <Text style={styles.buttonText}>
          {isLoading ? "Verifying…" : "Verify"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        onPress={() => {
          setShowRecovery((v) => !v);
          setCode("");
          setRecoveryCode("");
        }}
        accessibilityLabel={
          showRecovery ? "Use verification code" : "Use a recovery code"
        }
        style={styles.linkButton}
      >
        <Text style={styles.linkText}>
          {showRecovery ? "Use verification code" : "Use a recovery code"}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        onPress={onCancel}
        accessibilityLabel="Cancel"
        style={styles.linkButton}
      >
        <Text style={styles.cancelText}>Cancel</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: tokens.spacing[4],
  },
  label: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
  },
  destination: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[400],
  },
  inputGroup: {
    gap: tokens.spacing[1],
  },
  inputLabel: {
    fontSize: tokens.mobileFontSizes.bodyLg,
    lineHeight: tokens.mobileLineHeights.bodyLg,
    fontWeight: fontWeights.medium,
    color: tokens.colors.neutral[900],
  },
  input: {
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
    borderRadius: tokens.radii.md,
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
    minHeight: tokens.touchTargets.mobile.md,
  },
  error: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.fault[600],
  },
  button: {
    backgroundColor: tokens.colors.brand[600],
    borderRadius: tokens.radii.md,
    paddingVertical: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[4],
    minHeight: tokens.touchTargets.mobile.md,
    alignItems: "center",
    justifyContent: "center",
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    fontSize: tokens.mobileFontSizes.bodyLg,
    lineHeight: tokens.mobileLineHeights.bodyLg,
    fontWeight: fontWeights.medium,
    color: "#FFFFFF",
  },
  linkButton: {
    alignItems: "center",
    paddingVertical: tokens.spacing[2],
    minHeight: tokens.touchTargets.mobile.sm,
  },
  linkText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.brand[600],
  },
  cancelText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[400],
  },
});
