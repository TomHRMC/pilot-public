/**
 * Owner Tab — Full owner dashboard (MOB-B5 rewrite)
 *
 * Location: apps/mobile/app/(tabs)/owner.tsx
 *
 * Layout: SafeAreaView + ScrollView (replaces centered View from FE-B3 placeholder).
 * Section order (per design doc §G.6):
 *   1. ApprovalsQueueSection   — pending quote approvals (most time-sensitive)
 *   2. FieldIssuesSyncStatusSection — field issues (existing — preserved)
 *   3. CalendarSyncStatusSection    — calendar sync (existing — preserved)
 *   4. QbSyncStatusSection          — QuickBooks connection (new)
 *   5. ArSummarySection             — accounts receivable (new)
 *   6. PlanUsageSection             — plan/tier info (new)
 *   7. Sign-out button              — always at bottom
 *
 * Removed: "Owner-only dashboard content coming in FE-B3+" placeholder text.
 * Preserved: CalendarSyncStatusSection, FieldIssuesSyncStatusSection, sign-out logic.
 * Sign-out logic unchanged: queryClient.clear() + signOut() + router.replace("/(auth)/login")
 */

import React from "react";
import {
  Text,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StyleSheet,
} from "react-native";
import { useRouter } from "expo-router";
import { useQueryClient } from "@tanstack/react-query";
import { RoleGate } from "@pilot/ui/role-gate";
import { useAuth } from "@pilot/ui/auth";
import { tokens, fontWeights } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";

// Existing sections (preserve — do not modify internals)
import { CalendarSyncStatusSection } from "@/features/owner-tab/components/CalendarSyncStatusSection";
import { FieldIssuesSyncStatusSection } from "@/features/owner-tab/components/FieldIssuesSyncStatusSection";

// New sections (MOB-B5)
import { ApprovalsQueueSection } from "@/features/owner-tab/components/ApprovalsQueueSection";
import { QbSyncStatusSection } from "@/features/owner-tab/components/QbSyncStatusSection";
import { ArSummarySection } from "@/features/owner-tab/components/ArSummarySection";
import { PlanUsageSection } from "@/features/owner-tab/components/PlanUsageSection";

export default function OwnerTab() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();

  // Sign-out logic unchanged from pre-MOB-B5
  const handleSignOut = async () => {
    queryClient.clear();
    await signOut();
    router.replace("/(auth)/login");
  };

  return (
    <SafeAreaView style={styles.safeArea} testID="owner-tab-screen">
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Tab content is role-gated — hidden for non-owner roles */}
        <RoleGate role={["owner", "accountant"]}>
          {/* Screen header — replaces centered title, now top-aligned */}
          <Text style={styles.screenTitle}>Owner</Text>
          {/* NOTE: "coming in FE-B3+" placeholder REMOVED */}

          {/* Section 1: Approvals Queue — most time-sensitive */}
          <ApprovalsQueueSection />

          {/* Section 2: Field Issues (existing — FE-B9 — preserve) */}
          <FieldIssuesSyncStatusSection />

          {/* Section 3: Calendar Sync (existing — FE-B8 — preserve) */}
          <CalendarSyncStatusSection />

          {/* Section 4: QuickBooks Sync Status (new — MOB-B5) */}
          <QbSyncStatusSection />

          {/* Section 5: AR Summary (new — MOB-B5) */}
          <ArSummarySection />

          {/* Section 6: Plan Usage (new — MOB-B5) */}
          <PlanUsageSection />

          {/* Sign-out — always at bottom */}
          <TouchableOpacity
            onPress={() => void handleSignOut()}
            accessibilityLabel="Sign out"
            testID="signout-button"
            style={styles.signOutButton}
            activeOpacity={0.7}
          >
            <Text style={styles.signOutText}>Sign out</Text>
          </TouchableOpacity>
        </RoleGate>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: tokens.colors.neutral[100], // #F5F5F4 — page background
  },
  scrollContent: {
    padding: tokens.spacing[4],
    paddingBottom: tokens.spacing[10],
    gap: tokens.spacing[3],
  },
  screenTitle: {
    fontSize: tokens.mobileFontSizes.h1,
    lineHeight: tokens.mobileLineHeights.h1,
    fontWeight: fontWeights.medium,
    color: tokens.colors.neutral[900],
    marginBottom: tokens.spacing[2],
  },
  signOutButton: {
    marginTop: tokens.spacing[6],
    paddingVertical: tokens.spacing[2],
    paddingHorizontal: tokens.spacing[4],
    minHeight: tokens.touchTargets.mobile.sm,
    justifyContent: "center",
    alignItems: "center",
  },
  signOutText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: lightTheme.danger.bg,
  },
});
