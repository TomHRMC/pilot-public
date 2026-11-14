/**
 * ClockInOutSection — Clock in/out with GPS capture + ETC prompt
 *
 * Location: apps/mobile/features/jobs/components/detail/ClockInOutSection.tsx
 *
 * Clock In flow:
 *   1. Request GPS permission (soft failure — never blocks clock-in)
 *   2. Capture coords if permission granted (5 second timeout)
 *   3. Call useCreateTimeEntry.create({ jobId, userId, startedAt })
 *      NOTE: GPS captured locally but not sent to API — JobTimeEntryCreate
 *      does not have check_in_lat/check_in_lng fields yet.
 *      GPS captured locally but not sent — backend doesn't have lat/lng fields yet.
 *
 * Clock Out flow:
 *   1. Show ETC prompt modal ("How many hours are still remaining?")
 *   2. "Done": create with hoursRemainingEstimate
 *   3. "Skip": create without hoursRemainingEstimate
 *
 * Per batch-mob-b6-design.md Step 4 (GPS capture).
 * Per batch-mob-b2-design.md §F.4 (ETC Capture is PRD §3.15 requirement).
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  Pressable,
  Modal,
  TextInput,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from "react-native";
import * as Location from "expo-location";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useCreateTimeEntry } from "../../../offline-sync/hooks/useCreateTimeEntry";
import type { JobTimeEntry } from "../../hooks/useJobDetail";

interface ClockInOutSectionProps {
  jobId: string;
  userId: string;
  activeTimeEntry: JobTimeEntry | null;
  onRefetch?: () => void;
  testID?: string;
}

export function ClockInOutSection({
  jobId,
  userId,
  activeTimeEntry,
  onRefetch,
  testID,
}: ClockInOutSectionProps): React.ReactElement {
  const { create, isPending } = useCreateTimeEntry();
  const [showEtcPrompt, setShowEtcPrompt] = useState(false);
  const [hoursRemaining, setHoursRemaining] = useState("");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isCapturingGps, setIsCapturingGps] = useState(false);

  // ── Running timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!activeTimeEntry) {
      setElapsedSeconds(0);
      return;
    }
    const start = new Date(activeTimeEntry.started_at).getTime();
    // Compute initial elapsed immediately
    setElapsedSeconds(Math.floor((Date.now() - start) / 1000));

    const interval = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - start) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [activeTimeEntry?.started_at]);

  const formattedTime = [
    Math.floor(elapsedSeconds / 3600),
    Math.floor((elapsedSeconds % 3600) / 60),
    elapsedSeconds % 60,
  ]
    .map((n) => String(n).padStart(2, "0"))
    .join(":");

  // ── Clock In ───────────────────────────────────────────────────────────────
  const handleClockIn = useCallback(async () => {
    // GPS captured locally but not sent to API — backend doesn't have lat/lng fields yet.
    let _checkInLat: number | null = null;
    let _checkInLng: number | null = null;

    setIsCapturingGps(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === "granted") {
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
          timeInterval: 5000,
        });
        _checkInLat = loc.coords.latitude;
        _checkInLng = loc.coords.longitude;
      }
      // If denied: proceed without GPS (no error shown to user)
    } catch (gpsError) {
      // GPS failed (timeout, device error) — proceed without coordinates
      console.warn("[ClockInOutSection] GPS capture failed:", gpsError);
    } finally {
      setIsCapturingGps(false);
    }

    try {
      await create({
        jobId,
        userId,
        startedAt: new Date(),
        // GPS not sent — JobTimeEntryCreate doesn't support lat/lng yet
        // Captured: _checkInLat, _checkInLng (for future use)
      });
      onRefetch?.();
    } catch {
      Alert.alert("Error", "Failed to clock in. Please try again.");
    }
  }, [create, jobId, userId, onRefetch]);

  // ── Clock Out → shows ETC prompt ──────────────────────────────────────────
  const handleClockOutPress = useCallback(() => {
    setHoursRemaining("");
    setShowEtcPrompt(true);
  }, []);

  const handleEtcDone = useCallback(async () => {
    if (!activeTimeEntry) return;
    setShowEtcPrompt(false);
    const parsed = parseFloat(hoursRemaining);
    try {
      await create({
        jobId,
        userId,
        startedAt: new Date(activeTimeEntry.started_at),
        endedAt: new Date(),
        hoursRemainingEstimate: !isNaN(parsed) ? parsed : undefined,
      });
      onRefetch?.();
    } catch {
      Alert.alert("Error", "Failed to clock out. Please try again.");
    }
  }, [activeTimeEntry, hoursRemaining, create, jobId, userId, onRefetch]);

  const handleEtcSkip = useCallback(async () => {
    if (!activeTimeEntry) return;
    setShowEtcPrompt(false);
    try {
      await create({
        jobId,
        userId,
        startedAt: new Date(activeTimeEntry.started_at),
        endedAt: new Date(),
      });
      onRefetch?.();
    } catch {
      Alert.alert("Error", "Failed to clock out. Please try again.");
    }
  }, [activeTimeEntry, create, jobId, userId, onRefetch]);

  const isLoading = isPending || isCapturingGps;

  return (
    <View style={styles.container} testID={testID ?? "clock-in-out-section"}>
      <Text style={styles.sectionTitle}>CLOCK IN / CLOCK OUT</Text>

      {activeTimeEntry ? (
        // ── Clocked In State ────────────────────────────────────────────────
        <View style={styles.clockedInRow}>
          <View style={styles.timerContainer}>
            <Text style={styles.timerIcon}>⏱</Text>
            <Text
              style={styles.timerText}
              testID="elapsed-timer"
              accessibilityLabel={`Elapsed time: ${formattedTime}`}
            >
              {formattedTime}
            </Text>
          </View>
          <Pressable
            style={[
              styles.button,
              styles.buttonDanger,
              isLoading && styles.buttonDisabled,
            ]}
            onPress={handleClockOutPress}
            disabled={isLoading}
            accessibilityRole="button"
            accessibilityLabel="Clock Out"
            testID="clock-out-button"
          >
            {isLoading ? (
              <ActivityIndicator color={colors.neutral[50]} size="small" />
            ) : (
              <Text style={styles.buttonText}>Clock Out</Text>
            )}
          </Pressable>
        </View>
      ) : (
        // ── Clocked Out State ───────────────────────────────────────────────
        <Pressable
          style={[
            styles.button,
            styles.buttonPrimary,
            isLoading && styles.buttonDisabled,
          ]}
          onPress={handleClockIn}
          disabled={isLoading}
          accessibilityRole="button"
          accessibilityLabel="Clock In"
          testID="clock-in-button"
        >
          {isLoading ? (
            <ActivityIndicator color={colors.neutral[50]} size="small" />
          ) : (
            <>
              <Text style={styles.buttonIcon}>⏱</Text>
              <Text style={styles.buttonText}>Clock In</Text>
            </>
          )}
        </Pressable>
      )}

      {/* ETC Prompt Modal */}
      <Modal
        visible={showEtcPrompt}
        transparent
        animationType="fade"
        onRequestClose={() => setShowEtcPrompt(false)}
        testID="etc-prompt-modal"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard} accessibilityViewIsModal>
            <Text style={styles.modalTitle}>
              Clocked out at{" "}
              {new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </Text>
            <Text style={styles.modalQuestion}>
              Hours still remaining on this job?
            </Text>
            <TextInput
              style={styles.modalInput}
              value={hoursRemaining}
              onChangeText={setHoursRemaining}
              placeholder="e.g. 1.5"
              placeholderTextColor={colors.neutral[400]}
              keyboardType="decimal-pad"
              accessibilityLabel="Hours remaining input"
              testID="etc-hours-input"
              autoFocus
            />
            <Text style={styles.modalHint}>(e.g. 1.5 = 1h 30m)</Text>
            <View style={styles.modalActions}>
              <Pressable
                style={[styles.modalButton, styles.modalButtonSecondary]}
                onPress={handleEtcSkip}
                accessibilityRole="button"
                testID="etc-skip-button"
              >
                <Text style={styles.modalButtonSecondaryText}>Skip</Text>
              </Pressable>
              <Pressable
                style={[styles.modalButton, styles.modalButtonPrimary]}
                onPress={handleEtcDone}
                accessibilityRole="button"
                testID="etc-done-button"
              >
                <Text style={styles.modalButtonPrimaryText}>Done</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[3],
  },
  sectionTitle: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  clockedInRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: spacing[3],
  },
  timerContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
    flex: 1,
  },
  timerIcon: {
    fontSize: 20,
    lineHeight: 24,
  },
  timerText: {
    fontSize: mobileFontSizes.h1,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 30,
  },
  button: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 44,
    borderRadius: radii.md,
    paddingHorizontal: spacing[5],
    gap: spacing[2],
  },
  buttonPrimary: {
    backgroundColor: colors.brand[600],
  },
  buttonDanger: {
    backgroundColor: colors.fault[600],
    paddingHorizontal: spacing[4],
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonIcon: {
    fontSize: 18,
    lineHeight: 22,
  },
  buttonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  // Modal styles
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "center",
    alignItems: "center",
    padding: spacing[4],
  },
  modalCard: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.lg,
    padding: spacing[6],
    width: "100%",
    maxWidth: 360,
    gap: spacing[3],
  },
  modalTitle: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  modalQuestion: {
    fontSize: mobileFontSizes.h2,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 28,
  },
  modalInput: {
    backgroundColor: colors.neutral[900],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    fontSize: mobileFontSizes.h2,
    color: colors.neutral[50],
    lineHeight: 28,
    borderWidth: 1,
    borderColor: colors.neutral[600],
  },
  modalHint: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[400],
    lineHeight: 16,
  },
  modalActions: {
    flexDirection: "row",
    gap: spacing[3],
    marginTop: spacing[2],
  },
  modalButton: {
    flex: 1,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.md,
  },
  modalButtonPrimary: {
    backgroundColor: colors.brand[600],
  },
  modalButtonSecondary: {
    backgroundColor: colors.neutral[600],
  },
  modalButtonPrimaryText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
  modalButtonSecondaryText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[200],
    lineHeight: 20,
  },
});
