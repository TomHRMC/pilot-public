/**
 * PasswordResetFlow — mobile
 *
 * Location: apps/mobile/features/login/components/PasswordResetFlow.tsx
 *
 * Three-step password reset flow presented as a modal:
 *   Step 1: request-reset — email input → calls resetPassword()
 *   Step 2: enter-code   — code + new password + confirm
 *   Step 3: success      — confirmation, dismiss modal
 *
 * FE-B2: design doc §A.2 PasswordResetFlow (mobile)
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { tokens, fontWeights } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";

interface PasswordResetFlowProps {
  onSuccess: () => void;
  onDismiss: () => void;
}

type ResetStep = "request-reset" | "enter-code" | "success";

const PASSWORD_MIN_LENGTH = 12;
const PASSWORD_REGEX =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{12,}$/;

function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!local || !domain) return email;
  return `${local.slice(0, 1)}***@${domain}`;
}

export function PasswordResetFlow({
  onSuccess,
  onDismiss,
}: PasswordResetFlowProps) {
  const { addNotification } = useNotificationQueue();
  const [step, setStep] = useState<ResetStep>("request-reset");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);

  function validatePassword(pw: string): string[] {
    const errors: string[] = [];
    if (pw.length < PASSWORD_MIN_LENGTH) {
      errors.push(`At least ${PASSWORD_MIN_LENGTH} characters`);
    }
    if (!/[a-z]/.test(pw)) errors.push("One lowercase letter");
    if (!/[A-Z]/.test(pw)) errors.push("One uppercase letter");
    if (!/\d/.test(pw)) errors.push("One number");
    if (!/[^A-Za-z\d]/.test(pw)) errors.push("One special character");
    return errors;
  }

  async function handleRequestReset() {
    setIsLoading(true);
    try {
      const { resetPassword } = await import("aws-amplify/auth");
      await resetPassword({ username: email });
      setStep("enter-code");
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to send reset code. Try again.";
      addNotification({
        id: `reset-error-${Date.now()}`,
        severity: "error",
        title: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConfirmReset() {
    const errors = validatePassword(newPassword);
    setPasswordErrors(errors);
    if (errors.length > 0) return;

    if (newPassword !== confirmPassword) {
      addNotification({
        id: `reset-mismatch-${Date.now()}`,
        severity: "error",
        title: "Passwords do not match.",
      });
      return;
    }

    setIsLoading(true);
    try {
      const { confirmResetPassword } = await import("aws-amplify/auth");
      await confirmResetPassword({
        username: email,
        confirmationCode: code,
        newPassword,
      });
      setStep("success");
      onSuccess();
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to reset password. Check your code and try again.";
      addNotification({
        id: `reset-confirm-error-${Date.now()}`,
        severity: "error",
        title: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResendCode() {
    setIsLoading(true);
    try {
      const { resetPassword } = await import("aws-amplify/auth");
      await resetPassword({ username: email });
      addNotification({
        id: `resend-code-${Date.now()}`,
        severity: "success",
        title: "Code resent. Check your email.",
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to resend code.";
      addNotification({
        id: `resend-error-${Date.now()}`,
        severity: "error",
        title: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  if (step === "success") {
    return (
      <View style={styles.successContainer} accessibilityRole="summary">
        <Text style={styles.successTitle}>Password updated!</Text>
        <Text style={styles.successBody}>
          Your password has been successfully reset.
        </Text>
        <TouchableOpacity
          onPress={onDismiss}
          accessibilityLabel="Back to sign in"
          testID="success-signin-button"
          style={styles.primaryButton}
          activeOpacity={0.8}
        >
          <Text style={styles.primaryButtonText}>Back to sign in</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (step === "enter-code") {
    return (
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.flex}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.stepIndicator}>Step 2 of 2</Text>
          <Text style={styles.destinationHint}>
            Code sent to{" "}
            <Text style={styles.destinationEmail}>{maskEmail(email)}</Text>
          </Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Verification code</Text>
            <TextInput
              accessibilityLabel="Verification code"
              testID="reset-code-input"
              keyboardType="number-pad"
              maxLength={6}
              value={code}
              onChangeText={(t) => setCode(t.replace(/\D/g, ""))}
              placeholder="000000"
              textContentType="oneTimeCode"
              editable={!isLoading}
              style={styles.input}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>New password</Text>
            <TextInput
              accessibilityLabel="New password"
              testID="new-password-input"
              secureTextEntry
              autoComplete="new-password"
              value={newPassword}
              onChangeText={(t) => {
                setNewPassword(t);
                setPasswordErrors([]);
              }}
              editable={!isLoading}
              style={styles.input}
            />
            <Text style={styles.requirementsHint}>
              Min. {PASSWORD_MIN_LENGTH} chars with uppercase, lowercase,
              number, symbol
            </Text>
            {passwordErrors.map((e) => (
              <Text key={e} style={styles.errorText} accessibilityRole="alert">
                {e}
              </Text>
            ))}
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Confirm new password</Text>
            <TextInput
              accessibilityLabel="Confirm new password"
              testID="confirm-password-input"
              secureTextEntry
              autoComplete="new-password"
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              editable={!isLoading}
              style={styles.input}
            />
          </View>

          <TouchableOpacity
            onPress={() => void handleConfirmReset()}
            accessibilityLabel="Reset password"
            testID="reset-confirm-button"
            disabled={
              isLoading ||
              !code ||
              !newPassword ||
              !confirmPassword ||
              !PASSWORD_REGEX.test(newPassword)
            }
            style={[
              styles.primaryButton,
              (isLoading ||
                !code ||
                !newPassword ||
                !confirmPassword ||
                !PASSWORD_REGEX.test(newPassword)) &&
                styles.buttonDisabled,
            ]}
            activeOpacity={0.8}
          >
            <Text style={styles.primaryButtonText}>
              {isLoading ? "Resetting…" : "Reset password"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => void handleResendCode()}
            accessibilityLabel="Resend code"
            testID="resend-code-button"
            disabled={isLoading}
            style={styles.linkButton}
            activeOpacity={0.7}
          >
            <Text style={styles.linkText}>Resend code</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  // Step 1: request-reset
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.flex}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.stepIndicator}>Step 1 of 2</Text>
        <Text style={styles.instructions}>
          Enter your email and we&apos;ll send a reset code.
        </Text>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Email</Text>
          <TextInput
            accessibilityLabel="Email"
            testID="reset-email-input"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            value={email}
            onChangeText={setEmail}
            placeholder="you@example.com"
            placeholderTextColor={tokens.colors.neutral[400]}
            editable={!isLoading}
            style={styles.input}
          />
        </View>

        <TouchableOpacity
          onPress={() => void handleRequestReset()}
          accessibilityLabel="Send reset code"
          testID="send-reset-button"
          disabled={isLoading || !email}
          style={[
            styles.primaryButton,
            (isLoading || !email) && styles.buttonDisabled,
          ]}
          activeOpacity={0.8}
        >
          <Text style={styles.primaryButtonText}>
            {isLoading ? "Sending…" : "Send reset code"}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    gap: tokens.spacing[4],
    paddingBottom: tokens.spacing[6],
  },
  stepIndicator: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: lightTheme.brand.textOnMuted,
  },
  instructions: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
  },
  destinationHint: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
  },
  destinationEmail: {
    color: tokens.colors.neutral[900],
  },
  inputGroup: {
    gap: tokens.spacing[1],
  },
  label: {
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
  requirementsHint: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[400],
  },
  errorText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: lightTheme.danger.bg,
  },
  primaryButton: {
    backgroundColor: lightTheme.brand.bg,
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
  primaryButtonText: {
    fontSize: tokens.mobileFontSizes.bodyLg,
    lineHeight: tokens.mobileLineHeights.bodyLg,
    fontWeight: fontWeights.medium,
    color: lightTheme.brand.text,
  },
  linkButton: {
    alignItems: "center",
    paddingVertical: tokens.spacing[2],
    minHeight: tokens.touchTargets.mobile.sm,
  },
  linkText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: lightTheme.brand.textOnMuted,
  },
  successContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing[4],
    padding: tokens.spacing[4],
  },
  successTitle: {
    fontSize: tokens.mobileFontSizes.h1,
    lineHeight: tokens.mobileLineHeights.h1,
    fontWeight: fontWeights.medium,
    color: tokens.colors.neutral[900],
    textAlign: "center",
  },
  successBody: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
    textAlign: "center",
  },
});
