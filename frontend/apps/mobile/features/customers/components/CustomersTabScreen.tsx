/**
 * CustomersTabScreen — Main customers tab: search bar + FlatList
 *
 * Location: apps/mobile/features/customers/components/CustomersTabScreen.tsx
 *
 * Design doc Section F.5 (MOB-B3)
 *
 * Features:
 *   - Search bar with 300ms debounce → useCustomers(debouncedSearch)
 *   - FlatList of CustomerListItem cards with pull-to-refresh
 *   - Loading / error / empty states
 *   - "First 50" limit note when result count ≥ 50
 *   - Navigation to customer detail: router.push(`/(tabs)/customers/${id}`)
 */

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  FlatList,
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
} from "react-native";
import { router } from "expo-router";
import { colors, spacing, fontWeights } from "@pilot/ui/tokens";
import { useCustomers } from "../hooks/useCustomers";
import { CustomerListItem } from "./CustomerListItem";
import type { CustomerListItem as CustomerListItemData } from "../hooks/useCustomers";
import { CreateCustomerBottomSheet } from "./CreateCustomerBottomSheet";

export function CustomersTabScreen() {
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // 300ms debounce — debouncing in component, hook receives already-debounced string
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { customers, isLoading, isError, refetch, isFetching } =
    useCustomers(debouncedSearch);

  function handleCustomerPress(customerId: string) {
    router.push(`/(tabs)/customers/${customerId}` as any);
  }

  function renderEmpty() {
    if (isLoading) return null;

    if (debouncedSearch.trim()) {
      return (
        <View style={styles.center} testID="customers-search-empty">
          <Text style={styles.emptyText}>
            {`No customers match '${searchInput}'`}
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.center} testID="customers-empty">
        <Text style={styles.emptyText}>No customers found</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="customers-tab-screen">
      {/* Screen header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Customers</Text>
        <Pressable
          onPress={() => setShowCreate(true)}
          style={styles.addButton}
          accessibilityLabel="Add customer"
          accessibilityRole="button"
          testID="add-customer-button"
        >
          <Text style={styles.addButtonText}>+</Text>
        </Pressable>
      </View>

      {/* Search bar */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search customers…"
          placeholderTextColor={colors.neutral[400]}
          value={searchInput}
          onChangeText={setSearchInput}
          autoCapitalize="none"
          autoCorrect={false}
          clearButtonMode="while-editing"
          testID="customers-search-input"
          accessibilityLabel="Search customers"
        />
      </View>

      {/* Loading state */}
      {isLoading && (
        <View style={styles.center} testID="customers-loading">
          <ActivityIndicator
            color={colors.brand[600]}
            accessibilityLabel="Loading"
          />
        </View>
      )}

      {/* Error state */}
      {isError && !isLoading && (
        <View style={styles.center} testID="customers-error">
          <Text style={styles.errorText}>Failed to load customers</Text>
          <Pressable
            style={styles.retryButton}
            onPress={() => refetch()}
            testID="customers-retry-btn"
          >
            <Text style={styles.retryButtonText}>Try again</Text>
          </Pressable>
        </View>
      )}

      {/* Customer list */}
      {!isLoading && !isError && (
        <FlatList<CustomerListItemData>
          data={customers}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <CustomerListItem customer={item} onPress={handleCustomerPress} />
          )}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
          ListEmptyComponent={renderEmpty}
          ListFooterComponent={
            customers.length >= 50 ? (
              <View style={styles.limitNoteContainer}>
                <Text style={styles.limitNote}>
                  Showing first 50 customers — search to narrow results
                </Text>
              </View>
            ) : null
          }
          refreshControl={
            <RefreshControl
              refreshing={isFetching && !isLoading}
              onRefresh={() => refetch()}
              tintColor={colors.brand[600]}
            />
          }
          testID="customers-list"
          contentContainerStyle={
            customers.length === 0 ? styles.emptyListContent : undefined
          }
        />
      )}

      {/* Create Customer bottom sheet */}
      <CreateCustomerBottomSheet
        visible={showCreate}
        onClose={() => setShowCreate(false)}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[6],
    paddingTop: spacing[4],
    paddingBottom: spacing[2],
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  headerTitle: {
    color: colors.neutral[900],
    fontSize: 22,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 30,
  },
  addButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.brand[600],
    alignItems: "center",
    justifyContent: "center",
  },
  addButtonText: {
    color: "#FFFFFF",
    fontSize: 22,
    lineHeight: 26,
    fontWeight: String(fontWeights.medium) as "500",
  },
  searchContainer: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  searchInput: {
    backgroundColor: colors.neutral[100],
    borderRadius: 10,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    fontSize: 15,
    color: colors.neutral[900],
    minHeight: 36,
  },
  separator: {
    height: 1,
    backgroundColor: colors.neutral[100],
    marginLeft: spacing[6],
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing[6],
  },
  emptyListContent: {
    flexGrow: 1,
  },
  emptyText: {
    color: colors.neutral[400],
    fontSize: 15,
    lineHeight: 22,
    textAlign: "center",
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
  limitNoteContainer: {
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
  },
  limitNote: {
    color: colors.neutral[400],
    fontSize: 12,
    lineHeight: 18,
    textAlign: "center",
  },
});
