/**
 * TechPendingQuotesList — mobile list of tech's submitted quotes with status
 *
 * Location: apps/mobile/features/quote-approval-status/TechPendingQuotesList.tsx
 *
 * Route: (home)/quotes/pending
 */

import React from "react";
import { View, Text, FlatList, StyleSheet, RefreshControl } from "react-native";
import { router } from "expo-router";
import { colors, spacing } from "@pilot/ui/tokens";
import { useTechQuotes } from "./hooks/useTechQuotes";
import { TechQuoteStatusCard } from "./components/TechQuoteStatusCard";

export function TechPendingQuotesList() {
  const {
    data: quotes,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useTechQuotes();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <Text style={styles.loadingText}>Loading quotes…</Text>
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Failed to load quotes.</Text>
      </View>
    );
  }

  if (!quotes || quotes.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyTitle}>No quotes yet</Text>
        <Text style={styles.emptyBody}>
          Quotes you submit will appear here with their approval status.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>My Quotes</Text>
      <FlatList
        data={quotes}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TechQuoteStatusCard
            quote={item}
            onPress={(id) =>
              router.push(
                `/(tabs)/(home)/quotes/${id}` as Parameters<
                  typeof router.push
                >[0],
              )
            }
          />
        )}
        refreshControl={
          <RefreshControl
            refreshing={isFetching && !isLoading}
            onRefresh={() => void refetch()}
            tintColor={colors.brand[600]}
          />
        }
        contentContainerStyle={styles.listContent}
        accessibilityLabel="My submitted quotes"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  heading: {
    fontSize: 20,
    fontWeight: "500",
    color: colors.neutral[900],
    paddingHorizontal: spacing[4],
    paddingTop: spacing[4],
    paddingBottom: spacing[2],
  },
  listContent: {
    paddingHorizontal: spacing[4],
    paddingBottom: spacing[8],
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: spacing[6],
  },
  loadingText: {
    fontSize: 13,
    color: colors.neutral[400],
  },
  errorText: {
    fontSize: 13,
    color: colors.fault[600],
  },
  emptyTitle: {
    fontSize: 17,
    fontWeight: "500",
    color: colors.neutral[900],
    marginBottom: spacing[2],
    textAlign: "center",
  },
  emptyBody: {
    fontSize: 13,
    color: colors.neutral[600],
    textAlign: "center",
    lineHeight: 20,
  },
});
