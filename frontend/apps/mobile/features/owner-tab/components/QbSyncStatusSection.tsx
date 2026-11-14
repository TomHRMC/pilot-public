/**
 * QbSyncStatusSection — Owner tab: QuickBooks connection status
 *
 * Location: apps/mobile/features/owner-tab/components/QbSyncStatusSection.tsx
 *
 * Shows QB connection status. When disconnected, shows a deep-link to web settings.
 * NOTE: No last_sync_at displayed — not in QuickBooksConnectionStatus response.
 *
 * connection_status "active" + is_connected=true → "Connected" + company name
 * Otherwise → "Not connected — Connect →" with Linking.openURL deep-link
 *
 * MOB-B5
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  Linking,
  StyleSheet,
} from "react-native";
import { tokens, lightTheme } from "@pilot/ui/tokens";
import { useQbStatusMobile } from "../hooks/useQbStatusMobile";

const WEB_APP_BASE_URL =
  process.env.EXPO_PUBLIC_WEB_APP_URL ?? "https://app.pilotfortrades.com";

export function QbSyncStatusSection() {
  const { data: qb, isLoading } = useQbStatusMobile();

  const isConnected =
    qb?.is_connected === true && qb.connection_status === "active";

  const handleConnectPress = () => {
    void Linking.openURL(
      `${WEB_APP_BASE_URL}/settings/integrations/quickbooks`,
    );
  };

  if (isLoading) {
    return (
      <View style={styles.row} testID="qb-loading">
        <ActivityIndicator size="small" color={tokens.colors.neutral[400]} />
      </View>
    );
  }

  return (
    <View style={styles.row} testID="qb-sync-status-section">
      <View style={styles.labelRow}>
        <Text style={styles.sectionLabel}>QuickBooks</Text>
      </View>
      {isConnected ? (
        <View style={styles.statusRow}>
          <View style={[styles.dot, styles.dotGreen]} />
          <Text style={styles.valueText}>
            {/* NOTE: No last_sync_at in QB status response — do NOT display it */}
            Connected{qb?.company_name ? ` · ${qb.company_name}` : ""}
          </Text>
        </View>
      ) : (
        <Pressable
          onPress={handleConnectPress}
          testID="qb-connect-link"
          accessibilityRole="link"
          accessibilityLabel="Connect QuickBooks"
        >
          <View style={styles.statusRow}>
            <View style={[styles.dot, styles.dotOrange]} />
            <Text style={styles.linkText}>Not connected — Connect →</Text>
          </View>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    backgroundColor: "#FFFFFF",
    borderRadius: 8,
    padding: tokens.spacing[3],
    gap: tokens.spacing[1],
  },
  labelRow: {
    flexDirection: "row",
    alignItems: "center",
  },
  sectionLabel: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[600],
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[2],
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  dotGreen: {
    backgroundColor: tokens.colors.margin[600],
  },
  dotOrange: {
    backgroundColor: tokens.colors.alert[400],
  },
  valueText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[900],
  },
  linkText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: lightTheme.brand.bg,
  },
});
