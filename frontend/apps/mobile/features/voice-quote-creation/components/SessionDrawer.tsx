/**
 * SessionDrawer — hamburger overlay showing session history
 *
 * Location: apps/mobile/features/voice-quote-creation/components/SessionDrawer.tsx
 *
 * Rendered inside [sessionId].tsx as an overlay — not a route.
 * Matches the ChatGPT mobile pattern: tap ☰ → drawer slides in.
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  Modal,
} from "react-native";
import { colors, radii, spacing } from "../../../../../packages/ui/src/tokens";
import type { VoiceSession } from "../types-stub";
import { SessionListItem } from "./SessionListItem";

interface SessionDrawerProps {
  sessions: VoiceSession[];
  currentSessionId: string | null;
  onSelect: (id: string) => void;
  onNewSession: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export function SessionDrawer({
  sessions,
  currentSessionId,
  onSelect,
  onNewSession,
  isOpen,
  onClose,
}: SessionDrawerProps) {
  function handleSelect(id: string) {
    onSelect(id);
    onClose();
  }

  return (
    <Modal
      visible={isOpen}
      transparent
      animationType="slide"
      onRequestClose={onClose}
      accessibilityViewIsModal
    >
      <Pressable
        style={styles.backdrop}
        onPress={onClose}
        accessibilityLabel="Close sessions drawer"
      />
      <View style={styles.drawer} testID="session-drawer">
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Voice Sessions</Text>
          <Pressable
            onPress={onClose}
            style={styles.closeBtn}
            accessibilityRole="button"
            accessibilityLabel="Close drawer"
            testID="session-drawer-close"
          >
            <Text style={styles.closeText}>✕</Text>
          </Pressable>
        </View>

        {/* New session CTA */}
        <Pressable
          style={styles.newSessionBtn}
          onPress={() => {
            onNewSession();
            onClose();
          }}
          accessibilityRole="button"
          accessibilityLabel="Start new voice session"
          testID="new-session-btn"
        >
          <Text style={styles.newSessionText}>+ New Session</Text>
        </Pressable>

        {/* Session list */}
        <ScrollView
          style={styles.list}
          accessibilityRole="list"
          testID="session-list"
        >
          {sessions.map((session) => (
            <SessionListItem
              key={session.session_id}
              session={session}
              isActive={session.session_id === currentSessionId}
              onPress={() => handleSelect(session.session_id)}
            />
          ))}
          {sessions.length === 0 && (
            <View style={styles.emptyList}>
              <Text style={styles.emptyText}>No sessions yet</Text>
            </View>
          )}
        </ScrollView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  drawer: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    width: "80%",
    backgroundColor: colors.neutral[50],
    borderTopRightRadius: radii.xl,
    borderBottomRightRadius: radii.xl,
    shadowColor: colors.neutral[900],
    shadowOffset: { width: 2, height: 0 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[4],
    paddingTop: spacing[8],
    paddingBottom: spacing[4],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
  },
  headerTitle: {
    fontSize: 17,
    color: colors.neutral[900],
  },
  closeBtn: {
    minWidth: 44,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  closeText: {
    fontSize: 17,
    color: colors.neutral[600],
  },
  newSessionBtn: {
    margin: spacing[4],
    padding: spacing[3],
    backgroundColor: colors.brand[600],
    borderRadius: radii.md,
    alignItems: "center",
    minHeight: 44,
    justifyContent: "center",
  },
  newSessionText: {
    color: colors.neutral[50],
    fontSize: 15,
  },
  list: {
    flex: 1,
  },
  emptyList: {
    padding: spacing[6],
    alignItems: "center",
  },
  emptyText: {
    color: colors.neutral[400],
    fontSize: 14,
  },
});
