/**
 * Mobile Voice settings — FE-B11
 *
 * Location: apps/mobile/app/(tabs)/(home)/settings/voice.tsx
 */

import React from "react";
import {
  ScrollView,
  Text,
  View,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import {
  useMobileSettingsCatalog,
  MOBILE_SETTINGS_CATALOG_QUERY_KEY,
} from "../../../../features/settings/hooks/useMobileSettingsCatalog";
import { VoicePersonaSection } from "../../../../features/settings/components/VoicePersonaSection";
import { useQueryClient, useMutation } from "@tanstack/react-query";

export default function MobileVoiceSettings() {
  const { getCatalogEntry, isLoading, isError } = useMobileSettingsCatalog();
  const queryClient = useQueryClient();

  const { mutateAsync: writeUserOverride } = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: unknown }) => {
      const res = await fetch(`/api/v1/settings/${key}/user-override`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      if (!res.ok) throw new Error("Save failed.");
      return res.json();
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: MOBILE_SETTINGS_CATALOG_QUERY_KEY,
      });
    },
  });

  const { mutateAsync: revertUserOverride } = useMutation({
    mutationFn: async (key: string) => {
      const res = await fetch(`/api/v1/settings/${key}/user-override`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Revert failed.");
      return res.json();
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: MOBILE_SETTINGS_CATALOG_QUERY_KEY,
      });
    },
  });

  if (isError) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>Failed to load settings.</Text>
      </View>
    );
  }

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  const voicePersonaEntry = getCatalogEntry("voice_persona_tone");

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="mobile-voice-settings"
    >
      <Text style={styles.heading}>Voice &amp; AI</Text>

      <VoicePersonaSection
        catalogEntry={voicePersonaEntry}
        onSaveUserOverride={async (val: unknown) => {
          await writeUserOverride({ key: "voice_persona_tone", value: val });
        }}
        onRevertUserOverride={async () => {
          await revertUserOverride("voice_persona_tone");
        }}
        testID="mobile-voice-persona-section"
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: { padding: 16, gap: 8 },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  heading: {
    fontSize: 22,
    fontWeight: "500",
    color: "#111827",
    marginBottom: 8,
  },
  errorText: { fontSize: 14, color: "#DC2626" },
});
