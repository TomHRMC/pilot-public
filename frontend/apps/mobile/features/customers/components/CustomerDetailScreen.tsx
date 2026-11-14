/**
 * CustomerDetailScreen — Customer detail: header, contact, sites, message button
 *
 * Location: apps/mobile/features/customers/components/CustomerDetailScreen.tsx
 *
 * Design doc Section F.6 (MOB-B3)
 *
 * Renders (scrollable ScrollView):
 *   1. Header: ← Back, display_name, type badge
 *   2. Contact section: email row. Phone placeholder (TODO — not in CustomerResponse)
 *   3. Sites section: list from useCustomerSites — name + formatted address
 *   4. "Message Customer" button → router.push(`/(tabs)/customers/${customerId}/comms`)
 *   5. Loading state while customer or sites loading
 *   6. Error state with retry
 *
 * AddressResponse shape (verified from openapi.json):
 *   { line1, line2, line3, city, state, postal_code, country, ... }
 */

import React from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { router } from "expo-router";
import { colors, radii, spacing, fontWeights } from "@pilot/ui/tokens";
import { useCustomerDetail } from "../hooks/useCustomerDetail";
import { useCustomerSites } from "../hooks/useCustomerSites";
import type { CustomerSite, SiteAddress } from "../hooks/useCustomerSites";

interface CustomerDetailScreenProps {
  customerId: string;
}

// Hardcoded type badge map — no enum endpoint. See design doc §A.2.2.
const TYPE_BADGE: Record<string, { label: string; isBrand: boolean }> = {
  residential: { label: "Residential", isBrand: false },
  commercial: { label: "Commercial", isBrand: true },
};

function getTypeBadge(type: string): { label: string; isBrand: boolean } {
  return TYPE_BADGE[type] ?? { label: type, isBrand: false };
}

/**
 * Format a site address from the verified AddressResponse shape.
 * Fields: line1, line2, line3, city, state, postal_code, country
 */
function formatSiteAddress(address: SiteAddress | null): string {
  if (!address) return "";
  const { line1, city, state, postal_code } = address;
  if (line1 && city && state) {
    return postal_code
      ? `${line1}, ${city}, ${state} ${postal_code}`
      : `${line1}, ${city}, ${state}`;
  }
  if (line1) return line1;
  if (city && state) return `${city}, ${state}`;
  return "";
}

function SiteRow({ site }: { site: CustomerSite }) {
  const addressText = formatSiteAddress(site.address);

  return (
    <View style={styles.siteRow} testID={`site-row-${site.id}`}>
      <Text style={styles.siteName}>{site.name ?? "Unnamed site"}</Text>
      {addressText ? (
        <Text style={styles.siteAddress}>{addressText}</Text>
      ) : null}
    </View>
  );
}

export function CustomerDetailScreen({
  customerId,
}: CustomerDetailScreenProps) {
  const {
    customer,
    isLoading: customerLoading,
    isError: customerError,
    refetch,
  } = useCustomerDetail(customerId);
  const { sites, isLoading: sitesLoading } = useCustomerSites(customerId);

  const isLoading = customerLoading || sitesLoading;

  if (isLoading) {
    return (
      <View style={styles.center} testID="customer-detail-loading">
        <ActivityIndicator
          color={colors.brand[600]}
          accessibilityLabel="Loading"
        />
      </View>
    );
  }

  if (customerError || !customer) {
    return (
      <View style={styles.center} testID="customer-detail-error">
        <Text style={styles.errorText}>Failed to load customer</Text>
        <Pressable
          style={styles.retryButton}
          onPress={() => refetch()}
          testID="customer-detail-retry-btn"
        >
          <Text style={styles.retryButtonText}>Try again</Text>
        </Pressable>
      </View>
    );
  }

  const badge = getTypeBadge(customer.type);

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
      testID="customer-detail-screen"
    >
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          style={styles.backButton}
          onPress={() => router.back()}
          accessibilityLabel="Back"
          testID="customer-detail-back-btn"
        >
          <Text style={styles.backButtonText}>←</Text>
        </Pressable>
        <View style={styles.headerTitleRow}>
          <Text
            style={styles.headerTitle}
            numberOfLines={1}
            testID="customer-detail-name"
          >
            {customer.display_name}
          </Text>
          <View
            style={[
              styles.typeBadge,
              badge.isBrand ? styles.brandBadge : styles.neutralBadge,
            ]}
          >
            <Text
              style={[
                styles.typeBadgeText,
                badge.isBrand ? styles.brandBadgeText : styles.neutralBadgeText,
              ]}
            >
              {badge.label}
            </Text>
          </View>
        </View>
      </View>

      {/* Contact section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Contact</Text>

        {customer.email != null && (
          <View style={styles.contactRow}>
            <Text style={styles.contactIcon}>✉️</Text>
            <Text style={styles.contactValue} testID="customer-detail-email">
              {customer.email}
            </Text>
          </View>
        )}

        {/* TODO: mobile_phone not in CustomerResponse — request backend addition if needed */}
        <View style={styles.contactRow}>
          <Text style={styles.contactIcon}>📞</Text>
          <Text style={[styles.contactValue, styles.contactPlaceholder]}>
            (no phone on record)
          </Text>
        </View>
      </View>

      {/* Sites section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Sites</Text>
        {sites.length === 0 ? (
          <Text style={styles.noSitesText}>No sites on record</Text>
        ) : (
          sites.map((site) => <SiteRow key={site.id} site={site} />)
        )}
      </View>

      {/* Message Customer button */}
      <View style={styles.actionContainer}>
        <Pressable
          style={styles.messageButton}
          onPress={() =>
            router.push(`/(tabs)/customers/${customerId}/comms` as any)
          }
          accessibilityRole="button"
          testID="customer-detail-message-btn"
        >
          <Text style={styles.messageButtonText}>Message Customer</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  scrollContent: {
    paddingBottom: spacing[8],
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing[6],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[4],
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    gap: spacing[2],
  },
  backButton: {
    minWidth: 44,
    minHeight: 44,
    justifyContent: "center",
    alignItems: "flex-start",
  },
  backButtonText: {
    color: colors.brand[600],
    fontSize: 20,
  },
  headerTitleRow: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
    flexWrap: "wrap",
  },
  headerTitle: {
    flex: 1,
    color: colors.neutral[900],
    fontSize: 18,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 26,
  },
  typeBadge: {
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  brandBadge: {
    backgroundColor: colors.brand[50],
  },
  neutralBadge: {
    backgroundColor: colors.neutral[100],
  },
  typeBadgeText: {
    fontSize: 11,
    fontWeight: String(fontWeights.medium) as "500",
  },
  brandBadgeText: {
    color: colors.brand[800],
  },
  neutralBadgeText: {
    color: colors.neutral[600],
  },
  section: {
    backgroundColor: "#FFFFFF",
    marginTop: spacing[3],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[4],
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.neutral[200],
    gap: spacing[3],
  },
  sectionTitle: {
    color: colors.neutral[400],
    fontSize: 12,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 18,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  contactRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[3],
    minHeight: 32,
  },
  contactIcon: {
    fontSize: 16,
    width: 24,
    textAlign: "center",
  },
  contactValue: {
    flex: 1,
    color: colors.neutral[900],
    fontSize: 15,
    lineHeight: 22,
  },
  contactPlaceholder: {
    color: colors.neutral[400],
  },
  siteRow: {
    paddingVertical: spacing[2],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
    gap: spacing[1],
  },
  siteName: {
    color: colors.neutral[900],
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 22,
  },
  siteAddress: {
    color: colors.neutral[400],
    fontSize: 13,
    lineHeight: 18,
  },
  noSitesText: {
    color: colors.neutral[400],
    fontSize: 15,
    lineHeight: 22,
  },
  actionContainer: {
    paddingHorizontal: spacing[6],
    paddingTop: spacing[6],
  },
  messageButton: {
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    paddingVertical: spacing[3],
    paddingHorizontal: spacing[4],
    minHeight: 44,
    justifyContent: "center",
    alignItems: "center",
  },
  messageButtonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 22,
  },
  errorText: {
    color: colors.neutral[900],
    fontSize: 15,
    lineHeight: 22,
    marginBottom: spacing[3],
    textAlign: "center",
  },
  retryButton: {
    backgroundColor: colors.brand[600],
    borderRadius: 8,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    minHeight: 44,
    justifyContent: "center",
  },
  retryButtonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
  },
});
