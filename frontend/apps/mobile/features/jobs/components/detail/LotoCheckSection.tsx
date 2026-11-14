/**
 * LotoCheckSection — LOTO safety checklist with tenant-configurable policy gate
 *
 * Location: apps/mobile/features/jobs/components/detail/LotoCheckSection.tsx
 *
 * 3 hardcoded LOTO check types. When loto_confirmation_required = false (default):
 *   - Section remains visible (audit trail value — never hidden)
 *   - "Optional" badge shown next to section title
 *   - All check items remain tappable (audit capture still works)
 *   - Clock-out is NOT gated on LOTO completion
 * When loto_confirmation_required = true (required mode):
 *   - No "Optional" badge
 *   - Current required behavior preserved
 *
 * Per batch-mob-b7-design.md §F.3, §H.1
 */

import React, { useCallback } from "react";
import {
  View,
  Text,
  Pressable,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { useConfirmLoto } from "../../../offline-sync/hooks/useConfirmLoto";
import { useLotoPolicy } from "../../hooks/useLotoPolicy";

// ── Hardcoded check types ─────────────────────────────────────────────────────

const LOTO_CHECK_TYPES = [
  { checkType: "lockout_points", label: "Verify lockout points" },
  { checkType: "de_energized", label: "Test de-energized state" },
  { checkType: "tag_placement", label: "Confirm tag placement" },
] as const;

export interface LotoConfirmation {
  id: string;
  check_type: string;
  confirmed_at: string;
}

interface LotoCheckSectionProps {
  jobId: string;
  existingConfirmations: LotoConfirmation[];
  onRefetch?: () => void;
  testID?: string;
}

export function LotoCheckSection({
  jobId,
  existingConfirmations,
  onRefetch,
  testID,
}: LotoCheckSectionProps): React.ReactElement {
  const { confirm, isPending } = useConfirmLoto();

  // Policy gate: gracefully degrades to optional mode on error
  const { data: lotoPolicy } = useLotoPolicy();
  const isRequired = lotoPolicy?.loto_confirmation_required ?? false;

  const isConfirmed = useCallback(
    (checkType: string) =>
      existingConfirmations.some((c) => c.check_type === checkType),
    [existingConfirmations],
  );

  const handleConfirm = useCallback(
    async (checkType: string) => {
      try {
        await confirm({ jobId, checkType, confirmedAt: new Date() });
        onRefetch?.();
      } catch {
        // Silently queued offline
      }
    },
    [confirm, jobId, onRefetch],
  );

  return (
    <View style={styles.container} testID={testID ?? "loto-check-section"}>
      <View style={styles.titleRow}>
        <Text style={styles.sectionTitle}>LOTO SAFETY CHECK</Text>
        {!isRequired && (
          <View style={styles.optionalBadge} testID="loto-optional-badge">
            <Text style={styles.optionalBadgeText}>Optional</Text>
          </View>
        )}
      </View>

      {LOTO_CHECK_TYPES.map((item) => {
        const confirmed = isConfirmed(item.checkType);
        return (
          <Pressable
            key={item.checkType}
            style={[styles.checkRow, confirmed && styles.checkRowConfirmed]}
            onPress={
              confirmed ? undefined : () => void handleConfirm(item.checkType)
            }
            disabled={confirmed || isPending}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: confirmed, disabled: confirmed }}
            accessibilityLabel={item.label}
            testID={`loto-item-${item.checkType}`}
          >
            {isPending && !confirmed ? (
              <ActivityIndicator
                size="small"
                color={colors.brand[400]}
                style={styles.checkbox}
              />
            ) : (
              <Text
                style={[styles.checkbox, confirmed && styles.checkboxChecked]}
              >
                {confirmed ? "✅" : "☐"}
              </Text>
            )}
            <Text
              style={[
                styles.checkLabel,
                confirmed && styles.checkLabelConfirmed,
              ]}
            >
              {item.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[2],
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
    marginBottom: spacing[1],
  },
  sectionTitle: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  optionalBadge: {
    backgroundColor: colors.neutral[600],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: 2,
  },
  optionalBadgeText: {
    fontSize: 10,
    color: colors.neutral[400],
    fontWeight: String(fontWeights.medium) as "500",
    textTransform: "uppercase",
    letterSpacing: 0.3,
  },
  checkRow: {
    flexDirection: "row",
    alignItems: "center",
    minHeight: 44,
    paddingVertical: spacing[2],
    gap: spacing[3],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[1],
  },
  checkRowConfirmed: {
    opacity: 0.7,
  },
  checkbox: {
    fontSize: 20,
    lineHeight: 24,
    width: 24,
    textAlign: "center",
    color: colors.neutral[400],
  },
  checkboxChecked: {
    color: colors.margin[600],
  },
  checkLabel: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[50],
    lineHeight: 20,
    flex: 1,
  },
  checkLabelConfirmed: {
    color: colors.neutral[400],
  },
});
