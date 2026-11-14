/**
 * Home tab root screen — Today-First Layout
 *
 * Location: apps/mobile/app/(tabs)/(home)/index.tsx
 *
 * Layout (top to bottom):
 *   1. Compact voice CTA row — secondary position
 *   2. Today's Jobs — primary content (from useTechJobsList)
 *   3. Customer Messages section — bottom (existing CustomerMessagesSectionRow)
 *
 * Per batch-mob-b7-design.md §H.2 and PRD §3.14
 */

import React, { useCallback } from "react";
import {
  Text,
  Pressable,
  StyleSheet,
  ScrollView,
  View,
  ActivityIndicator,
  SafeAreaView,
} from "react-native";
import { useRouter } from "expo-router";
import {
  colors,
  radii,
  spacing,
  fontWeights,
} from "../../../../../packages/ui/src/tokens";
import { useVoiceSessions } from "../../../features/voice-quote-creation/hooks/useVoiceSessions";
import { CustomerMessagesSectionRow } from "../../../features/customer-comms/components/CustomerMessagesSectionRow";
import { useTechJobsList } from "../../../features/jobs/hooks/useTechJobsList";
import { JobCardRow } from "../../../features/jobs/components/JobCardRow";

// Expo Router types are generated from file structure. Until the new voice routes
// are registered in the generated types, we cast to bypass the strict check.
type AnyHref = Parameters<ReturnType<typeof useRouter>["push"]>[0];

function toHref(path: string): AnyHref {
  return path as AnyHref;
}

function formatTodayHeader(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

export default function HomeScreen() {
  const router = useRouter();
  const { createSession, isCreating } = useVoiceSessions();
  const { todaysJobs, isLoading: jobsLoading } = useTechJobsList();

  async function handleStartVoiceSession() {
    try {
      const newSession = await createSession();
      if (newSession && "session_id" in newSession) {
        router.push(
          toHref(`/voice/${(newSession as { session_id: string }).session_id}`),
        );
      }
    } catch {
      // Show error state
    }
  }

  function handleViewSessions() {
    router.push(toHref("/voice"));
  }

  const handleJobPress = useCallback(
    (jobId: string) => {
      router.push(toHref(`/jobs/${jobId}`));
    },
    [router],
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        style={styles.scrollRoot}
        contentContainerStyle={styles.root}
        testID="home-screen"
      >
        {/* 1. Compact voice CTA row — secondary position */}
        <View style={styles.voiceRow} testID="voice-cta-row">
          <Pressable
            style={[styles.voiceCta, isCreating && styles.voiceCtaDisabled]}
            onPress={handleStartVoiceSession}
            disabled={isCreating}
            accessibilityRole="button"
            accessibilityLabel="Start a voice session"
            testID="start-voice-session-btn"
          >
            <Text style={styles.voiceCtaText}>
              {isCreating ? "Starting…" : "🎙 Start Voice Session"}
            </Text>
          </Pressable>
          <Pressable
            style={styles.viewSessionsBtn}
            onPress={handleViewSessions}
            accessibilityRole="button"
            accessibilityLabel="View prior voice sessions"
            testID="view-sessions-btn"
          >
            <Text style={styles.viewSessionsText}>Sessions</Text>
          </Pressable>
        </View>

        {/* 2. Today's Jobs — primary content */}
        <View style={styles.todaySection} testID="today-jobs-section">
          <Text style={styles.todayHeader} testID="today-header">
            TODAY — {formatTodayHeader()}
          </Text>

          {jobsLoading ? (
            <ActivityIndicator
              size="small"
              color={colors.brand[600]}
              testID="jobs-loading"
            />
          ) : todaysJobs.length === 0 ? (
            <Text style={styles.emptyText} testID="no-jobs-today">
              No jobs scheduled today
            </Text>
          ) : (
            todaysJobs.map((job) => (
              <JobCardRow key={job.id} job={job} onPress={handleJobPress} />
            ))
          )}
        </View>

        {/* 3. Customer Messages — bottom */}
        <CustomerMessagesSectionRow testID="customer-messages-section" />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  scrollRoot: {
    flex: 1,
  },
  root: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    gap: spacing[4],
  },
  // Voice CTA row — compact, secondary
  voiceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[3],
    backgroundColor: "#FFFFFF",
    borderRadius: radii.md,
    padding: spacing[3],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  voiceCta: {
    flex: 1,
    backgroundColor: colors.brand[600],
    borderRadius: radii.sm,
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    alignItems: "center",
    justifyContent: "center",
    minHeight: 40,
  },
  voiceCtaDisabled: {
    opacity: 0.6,
  },
  voiceCtaText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: String(fontWeights.medium) as "500",
  },
  viewSessionsBtn: {
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    minHeight: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  viewSessionsText: {
    color: colors.brand[600],
    fontSize: 14,
    fontWeight: String(fontWeights.medium) as "500",
  },
  // Today's jobs section
  todaySection: {
    gap: spacing[2],
  },
  todayHeader: {
    fontSize: 13,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[600],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: spacing[1],
  },
  emptyText: {
    fontSize: 15,
    color: colors.neutral[400],
    textAlign: "center",
    paddingVertical: spacing[4],
  },
});
