/**
 * (home)/quotes/[id] — Tech-side quote detail with status and comments
 *
 * Location: apps/mobile/app/(tabs)/(home)/quotes/[id].tsx
 */

import { useLocalSearchParams } from "expo-router";
import { TechQuoteStatusDetail } from "@/features/quote-approval-status/TechQuoteStatusDetail";
import { useTechQuotes } from "@/features/quote-approval-status/hooks/useTechQuotes";
import { View, Text, ActivityIndicator, StyleSheet } from "react-native";
import { colors } from "@pilot/ui/tokens";

export default function TechQuoteDetailRoute() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: quotes, isLoading } = useTechQuotes();

  const quote = quotes?.find((q) => q.id === id);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.brand[600]} />
      </View>
    );
  }

  if (!quote) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>Quote not found.</Text>
      </View>
    );
  }

  return (
    <TechQuoteStatusDetail
      quoteId={quote.id}
      quoteNumber={quote.quote_number}
      status={quote.status}
      customerName={quote.customer_name}
      hasOwnerEdits={quote.has_owner_edits}
    />
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: colors.neutral[50],
  },
  errorText: {
    fontSize: 13,
    color: colors.fault[600],
  },
});
