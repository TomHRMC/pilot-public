/**
 * LoginForm — mobile
 *
 * Location: apps/mobile/features/login/components/LoginForm.tsx
 *
 * Email + password form for Cognito authentication on mobile.
 * Full-page loading overlay during sign-in.
 * In mock mode (EXPO_PUBLIC_USE_MOCK_AUTH=true): renders role-picker.
 *
 * FE-B2: design doc §A.2 LoginForm (mobile)
 */

import React, { useState, useRef, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Platform,
  ActivityIndicator,
  Modal,
} from "react-native";
import { useRouter } from "expo-router";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import type { PilotRole } from "@pilot/ui/auth";
import { tokens, fontWeights } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";
import { useLoginFlow } from "../hooks/useLoginFlow";
import { MfaChallengeStep } from "./MfaChallengeStep";
import { MfaEnrollmentRequiredGate } from "./MfaEnrollmentRequiredGate";

interface LoginFormProps {
  onSuccess: (role: PilotRole) => void;
  mockMode?: boolean;
}

const PILOT_ROLES: PilotRole[] = [
  "owner",
  "technician",
  "office_staff",
  "accountant",
];

function roleLabel(role: PilotRole): string {
  switch (role) {
    case "owner":
      return "Owner";
    case "technician":
      return "Technician";
    case "office_staff":
      return "Office Staff";
    case "accountant":
      return "Accountant";
    default:
      return role;
  }
}

function MockLoginForm({
  onSuccess,
  defaultRole,
}: {
  onSuccess: (role: PilotRole) => void;
  defaultRole: PilotRole;
}) {
  const [email, setEmail] = useState("mockuser@pilot-dev.example.com");
  const [selectedRole, setSelectedRole] = useState<PilotRole>(defaultRole);
  const { signIn } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const roleIndex = PILOT_ROLES.indexOf(selectedRole);

  const handleSignIn = async () => {
    setIsLoading(true);
    try {
      await signIn(email, "");
      onSuccess(selectedRole);
    } finally {
      setIsLoading(false);
    }
  };

  const cycleRole = () => {
    const next = PILOT_ROLES[(roleIndex + 1) % PILOT_ROLES.length];
    setSelectedRole(next!);
  };

  return (
    <View style={styles.form}>
      <View style={styles.devBadge}>
        <Text style={styles.devBadgeText}>DEV MODE — Mock Auth Active</Text>
      </View>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>Email</Text>
        <TextInput
          accessibilityLabel="Email"
          testID="mock-email-input"
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          value={email}
          onChangeText={setEmail}
          style={styles.input}
        />
      </View>

      <View style={styles.inputGroup}>
        <Text style={styles.label}>Role</Text>
        <TouchableOpacity
          onPress={cycleRole}
          accessibilityLabel={`Role: ${roleLabel(selectedRole)}. Tap to change.`}
          testID="mock-role-picker"
          style={styles.rolePicker}
          activeOpacity={0.7}
        >
          <Text style={styles.rolePickerText}>{roleLabel(selectedRole)}</Text>
          <Text style={styles.rolePickerChevron}>⌄</Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        onPress={() => void handleSignIn()}
        accessibilityLabel={`Sign in as ${roleLabel(selectedRole)}`}
        testID="mock-signin-button"
        disabled={isLoading}
        style={[styles.primaryButton, isLoading && styles.buttonDisabled]}
        activeOpacity={0.8}
      >
        <Text style={styles.primaryButtonText}>
          {isLoading ? "Signing in…" : `Sign in as ${roleLabel(selectedRole)}`}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

export function LoginForm({ onSuccess, mockMode = false }: LoginFormProps) {
  const router = useRouter();
  const { signOut } = useAuth();
  const { addNotification } = useNotificationQueue();
  const passwordRef = useRef<TextInput>(null);

  const {
    step,
    isLoading,
    error,
    mfaChallenge,
    submitCredentials,
    submitMfaCode,
    cancelMfa,
    clearError,
  } = useLoginFlow(onSuccess);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (error) {
      // Show in notification banner (for screens that have it)
      addNotification({
        id: `login-error-${Date.now()}`,
        severity: "error",
        title: error,
      });
      // Error is also shown inline below the button — don't clear yet
    }
  }, [error, addNotification]);

  const defaultRole =
    (process.env.EXPO_PUBLIC_MOCK_USER_ROLE as PilotRole | undefined) ??
    "owner";

  if (mockMode) {
    return <MockLoginForm onSuccess={onSuccess} defaultRole={defaultRole} />;
  }

  if (step === "mfa-enrollment-required") {
    return (
      <MfaEnrollmentRequiredGate
        onBeginEnrollment={() => router.push("/(tabs)/owner")}
        onSignOut={() => void signOut()}
      />
    );
  }

  if (step === "mfa-challenge" && mfaChallenge) {
    return (
      <MfaChallengeStep
        challengeName={mfaChallenge.challengeName}
        destination={mfaChallenge.destination}
        onConfirm={submitMfaCode}
        onCancel={cancelMfa}
        isLoading={isLoading}
        error={error}
      />
    );
  }

  const canSubmit = !isLoading && !!email && !!password;

  return (
    <>
      {/* Full-screen loading overlay rendered in a Modal so it always
          covers the entire screen regardless of parent layout */}
      <Modal
        visible={isLoading}
        transparent
        animationType="fade"
        statusBarTranslucent
      >
        <View style={styles.loadingOverlay} accessibilityRole="progressbar">
          <ActivityIndicator size="large" color={lightTheme.brand.bg} />
          <Text style={styles.loadingText}>Signing in…</Text>
        </View>
      </Modal>

      <View style={styles.form}>
        {/* Inline error banner — visible even without notification banner context */}
        {error ? (
          <View
            style={styles.inlineError}
            accessibilityRole="alert"
            accessibilityLiveRegion="polite"
          >
            <Text style={styles.inlineErrorText}>{error}</Text>
            <TouchableOpacity
              onPress={clearError}
              accessibilityLabel="Dismiss error"
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.inlineErrorDismiss}>✕</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Email</Text>
          <TextInput
            accessibilityLabel="Email"
            testID="login-email-input"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            autoCorrect={false}
            returnKeyType="next"
            value={email}
            onChangeText={setEmail}
            onSubmitEditing={() => passwordRef.current?.focus()}
            editable={!isLoading}
            placeholder="you@example.com"
            placeholderTextColor={tokens.colors.neutral[400]}
            style={styles.input}
          />
        </View>

        <View style={styles.inputGroup}>
          <Text style={styles.label}>Password</Text>
          {/* Password row: TextInput + show/hide toggle */}
          <View style={styles.passwordRow}>
            <TextInput
              ref={passwordRef}
              accessibilityLabel="Password"
              testID="login-password-input"
              secureTextEntry={!showPassword}
              autoComplete="password"
              returnKeyType="done"
              value={password}
              onChangeText={setPassword}
              onSubmitEditing={() => {
                if (canSubmit) {
                  void submitCredentials(email, password);
                }
              }}
              editable={!isLoading}
              style={[styles.input, styles.passwordInput]}
            />
            <TouchableOpacity
              onPress={() => setShowPassword((v) => !v)}
              accessibilityLabel={
                showPassword ? "Hide password" : "Show password"
              }
              testID="toggle-password-visibility"
              style={styles.eyeButton}
              activeOpacity={0.7}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.eyeIcon}>{showPassword ? "🙈" : "👁️"}</Text>
            </TouchableOpacity>
          </View>
        </View>

        <TouchableOpacity
          onPress={() => router.push("/(auth)/password-reset")}
          accessibilityLabel="Forgot password"
          testID="forgot-password-link"
          style={styles.forgotPasswordButton}
          activeOpacity={0.7}
        >
          <Text style={styles.forgotPasswordText}>Forgot password?</Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={() => void submitCredentials(email, password)}
          accessibilityLabel="Sign in"
          testID="login-submit-button"
          disabled={!canSubmit}
          style={[styles.primaryButton, !canSubmit && styles.buttonDisabled]}
          activeOpacity={0.8}
        >
          <Text style={styles.primaryButtonText}>Sign in</Text>
        </TouchableOpacity>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  form: {
    gap: tokens.spacing[4],
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
  // Password row: input takes remaining space, eye button overlaps right edge
  passwordRow: {
    flexDirection: "row",
    alignItems: "center",
    position: "relative",
  },
  passwordInput: {
    flex: 1,
    paddingRight: tokens.spacing[10], // make room for eye button (10 = 40px)
  },
  eyeButton: {
    position: "absolute",
    right: tokens.spacing[3],
    height: "100%",
    justifyContent: "center",
    alignItems: "center",
    minWidth: tokens.touchTargets.mobile.sm,
  },
  eyeIcon: {
    fontSize: 18,
  },
  forgotPasswordButton: {
    alignSelf: "flex-end",
    minHeight: tokens.touchTargets.mobile.sm,
    justifyContent: "center",
  },
  forgotPasswordText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: lightTheme.brand.textOnMuted,
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
  // Full-screen loading overlay (rendered in Modal so it covers everything)
  loadingOverlay: {
    flex: 1,
    backgroundColor: "rgba(255,255,255,0.92)",
    alignItems: "center",
    justifyContent: "center",
    gap: tokens.spacing[3],
  },
  loadingText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
  },
  // Inline error banner (always visible, regardless of notification banner context)
  // lightTheme uses "danger" not "error" — fall back to hardcoded red tones
  inlineError: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: lightTheme.danger?.bgMuted ?? "#FEF2F2",
    borderWidth: 1,
    borderColor: lightTheme.danger?.bg ?? "#DC2626",
    borderRadius: tokens.radii.md,
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    gap: tokens.spacing[2],
  },
  inlineErrorText: {
    flex: 1,
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: lightTheme.danger?.textOnMuted ?? "#991B1B",
  },
  inlineErrorDismiss: {
    fontSize: 14,
    color: lightTheme.danger?.textOnMuted ?? "#991B1B",
  },
  devBadge: {
    backgroundColor: lightTheme.warning.bgMuted,
    borderWidth: 1,
    borderColor: tokens.colors.alert[200],
    borderRadius: tokens.radii.sm,
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
    alignItems: "center",
  },
  devBadgeText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: lightTheme.warning.textOnMuted,
  },
  rolePicker: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
    borderRadius: tokens.radii.md,
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    minHeight: tokens.touchTargets.mobile.md,
  },
  rolePickerText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
  },
  rolePickerChevron: {
    fontSize: tokens.mobileFontSizes.body,
    color: tokens.colors.neutral[400],
  },
});
