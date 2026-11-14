/**
 * JobsTabScreen — Jobs tab root screen (MOB-B1)
 *
 * Location: apps/mobile/features/jobs/components/JobsTabScreen.tsx
 *
 * Replaces the 10-line jobs.tsx stub. Renders:
 *   - Today's assigned jobs (from useTechJobsList)
 *   - Upcoming jobs for next 7 days (collapsible, default expanded)
 *   - My Quotes navigation entry with pending count badge
 *
 * Uses apiClient via useTechJobsList (no raw fetch anywhere in this component).
 */

import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
} from "react-native";
import { useRouter } from "expo-router";
import { colors, spacing } from "@pilot/ui/tokens";
import { useTechJobsList } from "../hooks/useTechJobsList";
import { JobCardRow } from "./JobCardRow";
import { MyQuotesEntryRow } from "./MyQuotesEntryRow";

type AnyHref = Parameters<ReturnType<typeof useRouter>["push"]>[0];
function toHref(path: string): AnyHref {
  return path as AnyHref;
}

// ── Date header ───────────────────────────────────────────────────────────────

function formatTodayHeader(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// ── Section header ────────────────────────────────────────────────────────────

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  collapsible?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
  testID?: string;
}

function SectionHeader({
  title,
  subtitle,
  collapsible,
  expanded,
  onToggle,
  testID,
}: SectionHeaderProps) {
  return (
    <Pressable
      onPress={collapsible ? onToggle : undefined}
      style={styles.sectionHeader}
      accessibilityRole={collapsible ? "button" : undefined}
      accessibilityLabel={
        collapsible
          ? `${title}, ${expanded ? "collapse" : "expand"}`
          : undefined
      }
      testID={testID}
    >
      <View style={styles.sectionTitleRow}>
        <Text style={styles.sectionTitle}>{title}</Text>
        {subtitle && <Text style={styles.sectionSubtitle}>{subtitle}</Text>}
      </View>
      {collapsible && (
        <Text style={styles.collapseChevron} accessible={false}>
          {expanded ? "∧" : "∨"}
        </Text>
      )}
    </Pressable>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function JobsTabScreen() {
  const router = useRouter();
  const {
    todaysJobs,
    upcomingJobs,
    pendingQuoteCount,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useTechJobsList();

  const [upcomingExpanded, setUpcomingExpanded] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  }, [refetch]);

  const handleJobPress = useCallback(
    (jobId: string) => {
      router.push(toHref(`/jobs/${jobId}`));
    },
    [router],
  );

  const handleMyQuotesPress = useCallback(() => {
    router.push(toHref("/(tabs)/(home)/quotes/pending"));
  }, [router]);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <SafeAreaView style={styles.container} testID="jobs-tab-screen">
        <View style={styles.centered}>
          <ActivityIndicator
            size="large"
            color={colors.brand[600]}
            testID="jobs-loading-indicator"
          />
        </View>
      </SafeAreaView>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <SafeAreaView style={styles.container} testID="jobs-tab-screen">
        <View style={styles.centered}>
          <Text style={styles.errorText}>Failed to load jobs</Text>
          <Pressable
            onPress={() => void refetch()}
            style={styles.retryButton}
            accessibilityRole="button"
            testID="jobs-retry-button"
          >
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  // ── Main view ──────────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={styles.container} testID="jobs-tab-screen">
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing || (isFetching && !isLoading)}
            onRefresh={() => void handleRefresh()}
            tintColor={colors.brand[600]}
          />
        }
        testID="jobs-scroll-view"
      >
        {/* TODAY SECTION */}
        <SectionHeader
          title="TODAY"
          subtitle={formatTodayHeader()}
          testID="today-section-header"
        />

        {todaysJobs.length === 0 ? (
          <View style={styles.emptySection} testID="today-empty-state">
            <Text style={styles.emptyText}>No jobs scheduled for today</Text>
          </View>
        ) : (
          <View testID="today-jobs-list">
            {todaysJobs.map((job) => (
              <JobCardRow
                key={job.id}
                job={job}
                onPress={handleJobPress}
                testID={`today-job-${job.id}`}
              />
            ))}
          </View>
        )}

        {/* UPCOMING SECTION */}
        <SectionHeader
          title="UPCOMING"
          collapsible
          expanded={upcomingExpanded}
          onToggle={() => setUpcomingExpanded((prev) => !prev)}
          testID="upcoming-section-header"
        />

        {upcomingExpanded && (
          <>
            {upcomingJobs.length === 0 ? (
              <View style={styles.emptySection} testID="upcoming-empty-state">
                <Text style={styles.emptyText}>No upcoming jobs this week</Text>
              </View>
            ) : (
              <View testID="upcoming-jobs-list">
                {upcomingJobs.map((job) => (
                  <JobCardRow
                    key={job.id}
                    job={job}
                    onPress={handleJobPress}
                    testID={`upcoming-job-${job.id}`}
                  />
                ))}
              </View>
            )}
          </>
        )}

        {/* MY QUOTES ENTRY */}
        <View style={styles.quotesSection}>
          <MyQuotesEntryRow
            pendingCount={pendingQuoteCount}
            onPress={handleMyQuotesPress}
            testID="my-quotes-entry-row"
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[100],
  },
  scrollContent: {
    padding: spacing[4],
    gap: spacing[2],
    paddingBottom: spacing[8],
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing[4],
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: spacing[2],
    marginBottom: spacing[1],
  },
  sectionTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "600",
    color: colors.neutral[600],
    letterSpacing: 0.8,
    textTransform: "uppercase",
  },
  sectionSubtitle: {
    fontSize: 11,
    color: colors.neutral[400],
  },
  collapseChevron: {
    fontSize: 12,
    color: colors.neutral[400],
  },
  emptySection: {
    paddingVertical: spacing[4],
    alignItems: "center",
  },
  emptyText: {
    fontSize: 14,
    color: colors.neutral[400],
  },
  quotesSection: {
    marginTop: spacing[3],
  },
  errorText: {
    fontSize: 15,
    color: colors.neutral[600],
  },
  retryButton: {
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[4],
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  retryText: {
    fontSize: 15,
    color: colors.brand[600],
  },
});
