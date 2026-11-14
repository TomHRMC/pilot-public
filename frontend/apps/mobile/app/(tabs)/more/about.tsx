/**
 * Mobile About Screen — FE-B16
 *
 * Location: apps/mobile/app/(tabs)/more/about.tsx
 *
 * Route: /(tabs)/more/about
 * Version from Constants.expoConfig (not hardcoded).
 */

import React, { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  Pressable,
  Linking,
  Modal,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { Stack } from "expo-router";
import Constants from "expo-constants";

const APP_VERSION = Constants.expoConfig?.version ?? "dev";
const BUILD_NUMBER =
  Constants.expoConfig?.ios?.buildNumber ??
  String(Constants.expoConfig?.android?.versionCode ?? "");
const SUPPORT_EMAIL =
  process.env.EXPO_PUBLIC_SUPPORT_EMAIL ?? "support@pilotfortrades.com";
const MARKETING_URL =
  process.env.EXPO_PUBLIC_MARKETING_URL ?? "https://pilotfortrades.com";

const LEGAL_DOCS = [
  {
    id: "terms",
    label: "Terms of Service",
    url: `${MARKETING_URL}/legal/terms`,
  },
  {
    id: "privacy",
    label: "Privacy Policy",
    url: `${MARKETING_URL}/legal/privacy`,
  },
  { id: "eula", label: "EULA", url: `${MARKETING_URL}/legal/eula` },
] as const;

export default function AboutScreen() {
  const [legalModal, setLegalModal] = useState<{ title: string } | null>(null);

  const handleLegalPress = async (label: string, url: string) => {
    const supported = await Linking.canOpenURL(url);
    if (supported) {
      await Linking.openURL(url);
    } else {
      setLegalModal({ title: label });
    }
  };

  return (
    <SafeAreaView style={styles.container} testID="mobile-about-screen">
      <Stack.Screen
        options={{ title: "About Pilot", headerBackTitle: "More" }}
      />
      <ScrollView contentContainerStyle={styles.content}>
        {/* Version info */}
        <View style={styles.section} testID="about-version-block">
          <Text style={styles.sectionTitle}>App version</Text>
          <Text style={styles.versionText} testID="about-app-version">
            {APP_VERSION}
            {BUILD_NUMBER ? ` (${BUILD_NUMBER})` : ""}
          </Text>
          <Text style={styles.metaText}>
            Pilot for Trades © {new Date().getFullYear()}
          </Text>
        </View>

        {/* Legal links */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Legal</Text>
          {LEGAL_DOCS.map((doc) => (
            <Pressable
              key={doc.id}
              onPress={() => handleLegalPress(doc.label, doc.url)}
              style={({ pressed }) => [
                styles.linkRow,
                pressed && styles.pressed,
              ]}
              testID={`legal-link-${doc.id}`}
            >
              <Text style={styles.linkText}>{doc.label}</Text>
              <Text style={styles.chevron}>›</Text>
            </Pressable>
          ))}
        </View>

        {/* Contact */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Contact</Text>
          <Pressable
            onPress={() => Linking.openURL(`mailto:${SUPPORT_EMAIL}`)}
            style={({ pressed }) => [styles.linkRow, pressed && styles.pressed]}
            testID="about-support-email"
          >
            <Text style={styles.linkText}>{SUPPORT_EMAIL}</Text>
          </Pressable>
          <Pressable
            onPress={() => Linking.openURL(MARKETING_URL)}
            style={({ pressed }) => [styles.linkRow, pressed && styles.pressed]}
            testID="about-marketing-link"
          >
            <Text style={styles.linkText}>pilotfortrades.com</Text>
          </Pressable>
        </View>

        {/* Anonymization transparency */}
        <Text style={styles.anonText} testID="about-anon-statement">
          Pilot uses help conversations to improve our help content. Personal
          information is removed from conversations before they are used for any
          analysis or improvement purposes.
        </Text>
      </ScrollView>

      {/* Fallback modal */}
      <Modal
        visible={!!legalModal}
        animationType="slide"
        onRequestClose={() => setLegalModal(null)}
      >
        <SafeAreaView style={{ flex: 1, backgroundColor: "#fff" }}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{legalModal?.title}</Text>
            <Pressable onPress={() => setLegalModal(null)}>
              <Text style={styles.modalClose}>✕</Text>
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={{ padding: 20 }}>
            <Text style={{ color: "#6b7280", fontSize: 14 }}>
              Please visit {MARKETING_URL} to view this document.
            </Text>
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  content: { padding: 20 },
  section: { marginBottom: 28 },
  sectionTitle: {
    fontSize: 11,
    fontWeight: "600",
    color: "#9ca3af",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 8,
  },
  versionText: { fontSize: 14, color: "#6b7280", fontFamily: "monospace" },
  metaText: { fontSize: 12, color: "#9ca3af", marginTop: 2 },
  linkRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  pressed: { opacity: 0.6 },
  linkText: { fontSize: 14, color: "#2563eb" },
  chevron: { fontSize: 18, color: "#d1d5db" },
  anonText: { fontSize: 12, color: "#9ca3af", lineHeight: 18, marginTop: 8 },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  modalTitle: { fontSize: 16, fontWeight: "600", color: "#111827" },
  modalClose: { fontSize: 18, color: "#6b7280" },
});
