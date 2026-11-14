/**
 * AmpacityScreen — NEC Table 310.12 Ampacity Calculator
 *
 * Location: apps/mobile/features/nec-calcs/components/Ampacity/AmpacityScreen.tsx
 *
 * Form fields:
 *   - Wire Material: radio — Copper (only for MVP; aluminum not supported)
 *   - Wire Gauge: Picker — 14 AWG to 500 MCM
 *   - Temperature Rating: Picker — 60°C | 75°C | 90°C
 *   - Conductors in Bundle: numeric TextInput (default 3)
 *   - Ambient Temp (°C): numeric TextInput (default 30)
 *
 * Calls: calculate("ampacity", { wire_material, wire_gauge, temp_rating_c, conductor_count, ambient_temp_c })
 *
 * Per batch-mob-b4-design.md §F.5.
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
// Options
// ---------------------------------------------------------------------------

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

const TEMP_RATINGS = [
  { label: "60°C", value: 60 },
  { label: "75°C", value: 75 },
  { label: "90°C", value: 90 },
] as const;

function gaugeLabel(g: string): string {
  if (!isNaN(Number(g)) && Number(g) >= 250) return `${g} MCM`;
  return `${g} AWG`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AmpacityScreen() {
  const { result, isOfflineCalc, isLoading, error, calculate } =
    useNecCalculate();

  const [wireMaterial] = useState("copper"); // MVP: copper only
  const [wireGauge, setWireGauge] = useState("12");
  const [tempRating, setTempRating] = useState(75);
  const [conductorCount, setConductorCount] = useState("3");
  const [ambientTemp, setAmbientTemp] = useState("30");

  const handleCalculate = async () => {
    await calculate("ampacity", {
      wire_material: wireMaterial,
      wire_gauge: wireGauge,
      temp_rating_c: tempRating,
      conductor_count: parseInt(conductorCount, 10) || 3,
      ambient_temp_c: parseFloat(ambientTemp) || 30,
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
        <Text style={styles.title}>🔌 Ampacity</Text>
      </View>

      <ScrollView style={styles.scrollView} keyboardShouldPersistTaps="handled">
        {isOfflineCalc && <OfflineBanner />}

        {/* Wire Material — copper only for MVP */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Wire Material</Text>
          <View style={styles.chipRow}>
            <View style={[styles.chip, styles.chipSelected]}>
              <Text style={[styles.chipText, styles.chipTextSelected]}>
                Copper
              </Text>
            </View>
            {/* Aluminum — coming soon */}
            <View style={[styles.chip, styles.chipDisabled]}>
              <Text style={[styles.chipText, styles.chipTextDisabled]}>
                Aluminum (coming soon)
              </Text>
            </View>
          </View>
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

        {/* Temperature Rating */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Temperature Rating</Text>
          <View style={styles.chipRow}>
            {TEMP_RATINGS.map(({ label, value }) => (
              <Pressable
                key={value}
                onPress={() => setTempRating(value)}
                style={[
                  styles.chip,
                  tempRating === value && styles.chipSelected,
                ]}
                testID={`temp-rating-${value}`}
                accessibilityRole="button"
                accessibilityState={{ selected: tempRating === value }}
              >
                <Text
                  style={[
                    styles.chipText,
                    tempRating === value && styles.chipTextSelected,
                  ]}
                >
                  {label}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Conductors in Bundle */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Conductors in Bundle</Text>
          <TextInput
            style={styles.input}
            value={conductorCount}
            onChangeText={setConductorCount}
            keyboardType="numeric"
            placeholder="3"
            placeholderTextColor={tokens.colors.neutral[400]}
            testID="input-conductor-count"
            accessibilityLabel="Number of conductors in bundle"
          />
        </View>

        {/* Ambient Temperature */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Ambient Temperature (°C)</Text>
          <TextInput
            style={styles.input}
            value={ambientTemp}
            onChangeText={setAmbientTemp}
            keyboardType="numeric"
            placeholder="30"
            placeholderTextColor={tokens.colors.neutral[400]}
            testID="input-ambient-temp"
            accessibilityLabel="Ambient temperature in Celsius"
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
          <CalcResultDisplay result={result} testID="ampacity-result" />
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
    flexWrap: "wrap" as const,
    gap: tokens.spacing[2],
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
  chipDisabled: {
    opacity: 0.4,
  },
  chipText: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.neutral[600],
  },
  chipTextSelected: {
    color: "#fff",
    fontWeight: "600" as const,
  },
  chipTextDisabled: {
    color: tokens.colors.neutral[400],
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
