/**
 * Mobile Help Feedback Screen — FE-B16
 *
 * Location: apps/mobile/app/(tabs)/more/help/feedback.tsx
 *
 * Route: /(tabs)/more/help/feedback
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  Pressable,
  ScrollView,
  StyleSheet,
  Alert,
} from "react-native";
import { Stack } from "expo-router";
import { useMutation } from "@tanstack/react-query";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "";

type FeedbackCategory = "bug" | "feature_request" | "question" | "general";

const CATEGORIES: { value: FeedbackCategory; label: string }[] = [
  { value: "bug", label: "Bug report" },
  { value: "feature_request", label: "Feature request" },
  { value: "question", label: "Question" },
  { value: "general", label: "General feedback" },
];

export default function MobileFeedbackScreen() {
  const [category, setCategory] = useState<FeedbackCategory>("general");
  const [body, setBody] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/api/v1/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, body }),
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      return res.json();
    },
    onSuccess: () => {
      Alert.alert("Thanks!", "Your feedback has been received.", [
        {
          text: "OK",
          onPress: () => {
            setBody("");
            setCategory("general");
          },
        },
      ]);
      mutation.reset();
    },
  });

  return (
    <ScrollView style={styles.container} testID="mobile-feedback-screen">
      <Stack.Screen
        options={{ title: "Send feedback", headerBackTitle: "Help" }}
      />

      <View style={styles.content}>
        {/* Category */}
        <Text style={styles.sectionLabel}>Category</Text>
        {CATEGORIES.map((opt) => (
          <Pressable
            key={opt.value}
            onPress={() => setCategory(opt.value)}
            style={[
              styles.radioRow,
              category === opt.value && styles.radioRowSelected,
            ]}
            testID={`feedback-category-${opt.value}`}
          >
            <View
              style={[
                styles.radioCircle,
                category === opt.value && styles.radioCircleSelected,
              ]}
            />
            <Text style={styles.radioLabel}>{opt.label}</Text>
          </Pressable>
        ))}

        {/* Body */}
        <Text style={[styles.sectionLabel, { marginTop: 20 }]}>
          Your feedback
        </Text>
        <TextInput
          value={body}
          onChangeText={setBody}
          multiline
          numberOfLines={6}
          placeholder="Describe your feedback..."
          placeholderTextColor="#9ca3af"
          style={styles.textInput}
          testID="feedback-body-input"
        />
        <Text style={styles.charCount}>{body.length}/5000</Text>

        {/* Error */}
        {mutation.isError && (
          <Text style={styles.errorText}>
            {(mutation.error as Error)?.message ?? "Submission failed."}
          </Text>
        )}

        {/* Submit */}
        <Pressable
          onPress={() => mutation.mutate()}
          disabled={!body.trim() || mutation.isPending}
          style={({ pressed }) => [
            styles.submitBtn,
            (!body.trim() || mutation.isPending) && styles.submitBtnDisabled,
            pressed && styles.pressed,
          ]}
          testID="feedback-submit-btn"
          accessibilityLabel="Send feedback"
        >
          <Text style={styles.submitBtnText}>
            {mutation.isPending ? "Sending…" : "Send feedback"}
          </Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  content: { padding: 20 },
  sectionLabel: {
    fontSize: 13,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 10,
  },
  radioRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    marginBottom: 8,
  },
  radioRowSelected: { borderColor: "#2563eb", backgroundColor: "#eff6ff" },
  radioCircle: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: "#d1d5db",
  },
  radioCircleSelected: { borderColor: "#2563eb", backgroundColor: "#2563eb" },
  radioLabel: { fontSize: 14, color: "#374151" },
  textInput: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 8,
    padding: 12,
    fontSize: 14,
    color: "#111827",
    textAlignVertical: "top",
    minHeight: 120,
  },
  charCount: {
    color: "#9ca3af",
    fontSize: 11,
    textAlign: "right",
    marginTop: 4,
  },
  errorText: { color: "#dc2626", fontSize: 12, marginBottom: 8 },
  submitBtn: {
    backgroundColor: "#2563eb",
    borderRadius: 8,
    paddingVertical: 12,
    alignItems: "center",
    marginTop: 20,
  },
  submitBtnDisabled: { opacity: 0.4 },
  pressed: { opacity: 0.8 },
  submitBtnText: { color: "#fff", fontSize: 14, fontWeight: "600" },
});
