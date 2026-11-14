/**
 * VoltageDropScreen — NEC 210.19(A)(1) Voltage Drop Calculator
 *
 * Location: apps/mobile/features/nec-calcs/components/VoltageDrop/VoltageDropScreen.tsx
 *
 * Form fields:
 *   - Amps (A): numeric TextInput (required)
 *   - Distance (ft): numeric TextInput (required)
 *   - Wire Gauge: Picker — "14 AWG" to "500 MCM" (maps to bare gauge string)
 *   - Voltage (V): numeric TextInput (default 120)
 *   - Phase: radio — Single-Phase (1) | Three-Phase (3)
 *
 * Calls: calculate("voltage_drop", { amperage, distance_feet, wire_gauge, voltage, phase })
 *
 * Per batch-mob-b4-design.md §F.5 and §H.2.
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
// Wire gauge options — from AWG_CIRCULAR_MILS in nec_service.py
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
];

function gaugeLabel(g: string): string {
  // MCM gauges (250+)
  if (!isNaN(Number(g)) && Number(g) >= 250) return `${g} MCM`;
  return `${g} AWG`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function VoltageDropScreen() {
  const { result, isOfflineCalc, isLoading, error, calculate } =
    useNecCalculate();

  const [amperage, setAmperage] = useState("");
  const [distanceFeet, setDistanceFeet] = useState("");
  const [wireGauge, setWireGauge] = useState("12");
  const [voltage, setVoltage] = useState("120");
  const [phase, setPhase] = useState<1 | 3>(1);
  const [gaugeIndex, setGaugeIndex] = useState(1); // default index for "12"

  const handleCalculate = async () => {
    await calculate("voltage_drop", {
      amperage: parseFloat(amperage) || 0,
      distance_feet: parseFloat(distanceFeet) || 0,
      wire_gauge: wireGauge,
      voltage: parseFloat(voltage) || 120,
      phase,
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
        <Text style={styles.title}>⚡ Voltage Drop</Text>
      </View>

      <ScrollView style={styles.scrollView} keyboardShouldPersistTaps="handled">
        {/* Offline banner — shown when offline engine was used */}
        {isOfflineCalc && <OfflineBanner />}

        {/* Amperage */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Amps (A)</Text>
          <TextInput
            style={styles.input}
            value={amperage}
            onChangeText={setAmperage}
            keyboardType="numeric"
            placeholder="e.g. 20"
            placeholderTextColor={tokens.colors.neutral[400]}
            testID="input-amperage"
            accessibilityLabel="Amperage in amps"
          />
        </View>

        {/* Distance */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Distance (ft)</Text>
          <TextInput
            style={styles.input}
            value={distanceFeet}
            onChangeText={setDistanceFeet}
            keyboardType="numeric"
            placeholder="e.g. 100"
            placeholderTextColor={tokens.colors.neutral[400]}
            testID="input-distance"
            accessibilityLabel="Distance in feet"
          />
        </View>

        {/* Wire Gauge Picker */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Wire Gauge</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.pickerScroll}
            testID="picker-wire-gauge"
          >
            {WIRE_GAUGES.map((g, idx) => (
              <Pressable
                key={g}
                onPress={() => {
                  setWireGauge(g);
                  setGaugeIndex(idx);
                }}
                style={[
                  styles.pickerChip,
                  wireGauge === g && styles.pickerChipSelected,
                ]}
                testID={`gauge-option-${g}`}
                accessibilityRole="button"
                accessibilityState={{ selected: wireGauge === g }}
              >
                <Text
                  style={[
                    styles.pickerChipText,
                    wireGauge === g && styles.pickerChipTextSelected,
                  ]}
                >
                  {gaugeLabel(g)}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        {/* Voltage */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Voltage (V)</Text>
          <TextInput
            style={styles.input}
            value={voltage}
            onChangeText={setVoltage}
            keyboardType="numeric"
            placeholder="120"
            placeholderTextColor={tokens.colors.neutral[400]}
            testID="input-voltage"
            accessibilityLabel="Voltage in volts"
          />
        </View>

        {/* Phase radio */}
        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Phase</Text>
          <View style={styles.radioGroup}>
            <Pressable
              onPress={() => setPhase(1)}
              style={styles.radioOption}
              testID="phase-single"
              accessibilityRole="radio"
              accessibilityState={{ checked: phase === 1 }}
            >
              <View
                style={[
                  styles.radioCircle,
                  phase === 1 && styles.radioSelected,
                ]}
              />
              <Text style={styles.radioLabel}>Single-Phase</Text>
            </Pressable>
            <Pressable
              onPress={() => setPhase(3)}
              style={styles.radioOption}
              testID="phase-three"
              accessibilityRole="radio"
              accessibilityState={{ checked: phase === 3 }}
            >
              <View
                style={[
                  styles.radioCircle,
                  phase === 3 && styles.radioSelected,
                ]}
              />
              <Text style={styles.radioLabel}>Three-Phase</Text>
            </Pressable>
          </View>
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
          <CalcResultDisplay result={result} testID="voltage-drop-result" />
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
    backgroundColor: tokens.colors.neutral[50],
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
  pickerScroll: { flexDirection: "row" },
  pickerChip: {
    paddingHorizontal: tokens.spacing[3],
    paddingVertical: tokens.spacing[2],
    borderRadius: tokens.radii.full,
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
    marginRight: tokens.spacing[2],
    backgroundColor: "#fff",
  },
  pickerChipSelected: {
    backgroundColor: tokens.colors.brand[600],
    borderColor: tokens.colors.brand[600],
  },
  pickerChipText: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.neutral[600],
  },
  pickerChipTextSelected: {
    color: "#fff",
    fontWeight: "600" as const,
  },
  radioGroup: {
    flexDirection: "row",
    gap: tokens.spacing[6],
  },
  radioOption: {
    flexDirection: "row",
    alignItems: "center",
    gap: tokens.spacing[2],
  },
  radioCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: tokens.colors.neutral[400],
    backgroundColor: "#fff",
  },
  radioSelected: {
    borderColor: tokens.colors.brand[600],
    backgroundColor: tokens.colors.brand[600],
  },
  radioLabel: {
    fontSize: tokens.webFontSizes.body,
    color: tokens.colors.neutral[800],
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
