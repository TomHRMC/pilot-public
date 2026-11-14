/**
 * JobNotesSection — Job notes text area + save
 *
 * Location: apps/mobile/features/jobs/components/detail/JobNotesSection.tsx
 *
 * Fetches GET /api/v1/jobs/{jobId}/notes on mount to pre-populate text area.
 * Returns a single object (not an array). 404 = no notes yet → empty text area.
 *
 * Save → useCreateJobNote.create({ jobId, createdBy, content }) (WatermelonDB).
 * SyncOrchestrator sends PUT /api/v1/jobs/{jobId}/notes on reconnect.
 *
 * Per batch-mob-b2-design.md §F.9 and §G.7.
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useCreateJobNote } from "../../../offline-sync/hooks/useCreateJobNote";

// ── API response type ─────────────────────────────────────────────────────────

interface JobNotesResponse {
  id: string;
  tenant_id: string;
  job_id: string;
  notes: string | null;
  audio_object_key: string | null;
  customer_visible: boolean;
  client_capture_at: string | null;
  server_received_at: string | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

interface JobNotesSectionProps {
  jobId: string;
  userId: string;
  testID?: string;
}

export function JobNotesSection({
  jobId,
  userId,
  testID,
}: JobNotesSectionProps): React.ReactElement {
  const [noteText, setNoteText] = useState("");
  const [isSaved, setIsSaved] = useState(false);

  const { create, isPending: isSaving } = useCreateJobNote();

  const { data: notesData, isLoading } = useQuery({
    queryKey: ["job-notes", jobId] as const,
    queryFn: async () => {
      try {
        const r = await apiClient.get<JobNotesResponse>(
          `/api/v1/jobs/${jobId}/notes`,
        );
        return r.data;
      } catch (err: unknown) {
        // 404 means no notes exist yet — return null gracefully
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr?.response?.status === 404) return null;
        throw err;
      }
    },
    enabled: !!jobId,
    staleTime: 60_000,
    retry: (failureCount, error: unknown) => {
      const axiosErr = error as { response?: { status?: number } };
      if (axiosErr?.response?.status === 404) return false;
      return failureCount < 2;
    },
  });

  // Pre-populate text area from server state when data loads
  useEffect(() => {
    if (notesData?.notes != null && noteText === "") {
      setNoteText(notesData.notes);
    }
    // Only run when data first arrives
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notesData?.notes]);

  const handleSave = useCallback(async () => {
    if (!noteText.trim()) {
      Alert.alert("Empty notes", "Please enter notes before saving.");
      return;
    }
    try {
      await create({
        jobId,
        createdBy: userId,
        content: noteText.trim(),
      });
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch {
      Alert.alert("Error", "Failed to save notes. Please try again.");
    }
  }, [noteText, create, jobId, userId]);

  return (
    <View style={styles.container} testID={testID ?? "job-notes-section"}>
      <Text style={styles.sectionTitle}>JOB NOTES</Text>

      {isLoading ? (
        <ActivityIndicator color={colors.brand[400]} style={styles.loader} />
      ) : (
        <>
          <TextInput
            style={styles.textArea}
            value={noteText}
            onChangeText={(text) => {
              setNoteText(text);
              setIsSaved(false);
            }}
            placeholder="Add field notes, observations, issues found..."
            placeholderTextColor={colors.neutral[400]}
            multiline
            numberOfLines={5}
            textAlignVertical="top"
            accessibilityLabel="Job notes"
            testID="job-notes-input"
          />

          <Pressable
            style={[
              styles.saveButton,
              (isSaving || isSaved) && styles.saveButtonDisabled,
            ]}
            onPress={handleSave}
            disabled={isSaving || isSaved}
            accessibilityRole="button"
            accessibilityLabel="Save notes"
            testID="save-notes-button"
          >
            {isSaving ? (
              <ActivityIndicator color={colors.neutral[50]} size="small" />
            ) : (
              <Text style={styles.saveButtonText}>
                {isSaved ? "✓ Saved" : "Save Notes"}
              </Text>
            )}
          </Pressable>
        </>
      )}
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
  loader: {
    alignSelf: "flex-start",
  },
  textArea: {
    backgroundColor: colors.neutral[900],
    borderRadius: radii.sm,
    borderWidth: 1,
    borderColor: colors.neutral[600],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[3],
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 22,
    minHeight: 120,
  },
  saveButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    fontSize: mobileFontSizes.body,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[50],
    lineHeight: 20,
  },
});
