/**
 * ConduitFillScreen — NEC Chapter 9 Table 1 Conduit Fill Calculator
 *
 * Location: apps/mobile/features/nec-calcs/components/ConduitFill/ConduitFillScreen.tsx
 *
 * Form fields:
 *   - Conduit Type: Picker — EMT | RMC | PVC40
 *   - Conduit Size: Picker — 1/2" to 4"
 *   - Wire Gauge: Picker — 14 AWG to 500 MCM
 *   - Number of Conductors: numeric TextInput
 *
 * Calls: calculate("conduit_fill", { conduit_trade_size, conduit_type, wire_gauge, num_conductors })
 *
 * Per batch-mob-b4-design.md §F.5 and §G.6.
 */

import React, { useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  View,
  Text,
  TextInput,
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { router } from "expo-router";
import { tokens } from "@pilot/ui/tokens";
import { useNecCalculate } from "../../hooks/useNecCalculate";
import { OfflineBanner } from "../OfflineBanner";
import { CalcResultDisplay } from "../CalcResultDisplay";

// ---------------------------------------------------------------------------
// Options from nec_service.py _CONDUIT_AREA_SQ_IN
// ---------------------------------------------------------------------------

const CONDUIT_TYPES = ["EMT", "RMC", "PVC40"] as const;
const CONDUIT_SIZES = [
  "1/2",
  "3/4",
  "1",
  "1-1/4",
  "1-1/2",
  "2",
  "2-1/2",
  "3",
  "3-1/2",
  "4",
] as const;
const WIRE_GAUGES = [
  "14",
  "12",
  "10",
  "8",
  "6",
  "4",
  "3",
  "2",
  "1",
  "1/0",
  "2/0",
  "3/0",
  "4/0",
  "250",
  "300",
  "350",
  "400",
  "500",
] as const;

function gaugeLabel(g: string): string {
  if (!isNaN(Number(g)) && Number(g) >= 250) return `${g} MCM`;
  return `${g} AWG`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ConduitFillScreen() {
  const { result, isOfflineCalc, isLoading, error, calculate } =
    useNecCalculate();

  const [conduitType, setConduitType] = useState<string>("EMT");
  const [conduitSize, setConduitSize] = useState<string>("3/4");
  const [wireGauge, setWireGauge] = useState<string>("12");
  const [numConductors, setNumConductors] = useState("");

  const handleCalculate = async () => {
    await calculate("conduit_fill", {
      conduit_trade_size: conduitSize,
      conduit_type: conduitType,
      wire_gauge: wireGauge,
      num_conductors: parseInt(numConductors, 10) || 0,
    });
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backBtn}
          accessibilityRole="button"
          accessibilityLabel="Back to Calcs"
          testID="back-button"
        >
          <Text style={styles.backText}>← Calcs</Text>
        </Pressable>
        <Text style={styles.title}>📐 Conduit Fill</Text>
      </View>

      <ScrollView style={styles.scrollView} keyboardShouldPersistTaps="handled">
        {isOfflineCalc && <OfflineBanner />}

        {/* Conduit Type */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Conduit Type</Text>
          <View style={styles.chipRow}>
            {CONDUIT_TYPES.map((t) => (
              <Pressable
                key={t}
                onPress={() => setConduitType(t)}
                style={[styles.chip, conduitType === t && styles.chipSelected]}
                testID={`conduit-type-${t}`}
                accessibilityRole="button"
                accessibilityState={{ selected: conduitType === t }}
              >
                <Text
                  style={[
                    styles.chipText,
                    conduitType === t && styles.chipTextSelected,
                  ]}
                >
                  {t}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Conduit Size */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Conduit Size (inches)</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            testID="picker-conduit-size"
          >
            {CONDUIT_SIZES.map((s) => (
              <Pressable
                key={s}
                onPress={() => setConduitSize(s)}
                style={[styles.chip, conduitSize === s && styles.chipSelected]}
                testID={`conduit-size-${s}`}
                accessibilityRole="button"
                accessibilityState={{ selected: conduitSize === s }}
              >
                <Text
                  style={[
                    styles.chipText,
                    conduitSize === s && styles.chipTextSelected,
                  ]}
                >
                  {s}"
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* Wire Gauge */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Wire Gauge</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            testID="picker-wire-gauge"
          >
            {WIRE_GAUGES.map((g) => (
              <Pressable
                key={g}
                onPress={() => setWireGauge(g)}
                style={[styles.chip, wireGauge === g && styles.chipSelected]}
                testID={`gauge-option-${g}`}
                accessibilityRole="button"
                accessibilityState={{ selected: wireGauge === g }}
              >
                <Text
                  style={[
                    styles.chipText,
                    wireGauge === g && styles.chipTextSelected,
                  ]}
                >
                  {gaugeLabel(g)}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* Number of Conductors */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Number of Conductors</Text>
          <TextInput
            style={styles.input}
            value={numConductors}
            onChangeText={setNumConductors}
            keyboardType="numeric"
            placeholder="e.g. 3"
            placeholderTextColor={tokens.colors.neutral[400]}
            testID="input-num-conductors"
            accessibilityLabel="Number of conductors"
          />
        </View>

        {/* Calculate button */}
        <Pressable
          onPress={handleCalculate}
          style={({ pressed }) => [
            styles.calcBtn,
            pressed && styles.calcBtnPressed,
          ]}
          testID="calculate-button"
          accessibilityRole="button"
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" testID="loading-indicator" />
          ) : (
            <Text style={styles.calcBtnText}>Calculate</Text>
          )}
        </Pressable>

        {/* Error */}
        {error != null && (
          <View style={styles.errorBox} testID="error-message">
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* Result */}
        {result != null && (
          <CalcResultDisplay result={result} testID="conduit-fill-result" />
        )}

        <View style={styles.bottomPad} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: tokens.colors.neutral[50] },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: tokens.spacing[4],
    paddingVertical: tokens.spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: tokens.colors.neutral[200],
  },
  backBtn: { marginRight: tokens.spacing[3] },
  backText: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.brand[600],
    fontWeight: "500" as const,
  },
  title: {
    fontSize: tokens.webFontSizes.h2,
    fontWeight: "700" as const,
    color: tokens.colors.neutral[900],
  },
  scrollView: { flex: 1 },
  fieldGroup: {
    paddingHorizontal: tokens.spacing[4],
    paddingTop: tokens.spacing[4],
  },
  label: {
    fontSize: tokens.webFontSizes.body,
    fontWeight: "500" as const,
    color: tokens.colors.neutral[800],
    marginBottom: tokens.spacing[1],
  },
  input: {
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
    borderRadius: tokens.radii.md,
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
    fontSize: tokens.webFontSizes.bodyLg,
    color: tokens.colors.neutral[900],
    backgroundColor: "#fff",
  },
  chipRow: {
    flexDirection: "row",
    gap: tokens.spacing[2],
    flexWrap: "wrap" as const,
  },
  chip: {
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
    borderRadius: tokens.radii.full,
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
    marginRight: tokens.spacing[2],
    marginBottom: tokens.spacing[1],
    backgroundColor: "#fff",
  },
  chipSelected: {
    backgroundColor: tokens.colors.brand[600],
    borderColor: tokens.colors.brand[600],
  },
  chipText: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.neutral[600],
  },
  chipTextSelected: {
    color: "#fff",
    fontWeight: "600" as const,
  },
  calcBtn: {
    marginHorizontal: tokens.spacing[4],
    marginTop: tokens.spacing[6],
    paddingVertical: tokens.spacing[3],
    borderRadius: tokens.radii.md,
    backgroundColor: tokens.colors.brand[600],
    alignItems: "center" as const,
  },
  calcBtnPressed: { opacity: 0.85 },
  calcBtnText: {
    fontSize: tokens.webFontSizes.bodyLg,
    fontWeight: "700" as const,
    color: "#fff",
  },
  errorBox: {
    marginHorizontal: tokens.spacing[4],
    marginTop: tokens.spacing[3],
    padding: tokens.spacing[3],
    backgroundColor: tokens.colors.fault[100],
    borderRadius: tokens.radii.md,
    borderWidth: 1,
    borderColor: tokens.colors.fault[200],
  },
  errorText: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.fault[800],
  },
  bottomPad: { height: tokens.spacing[12] },
});
