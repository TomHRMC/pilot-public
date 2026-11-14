/**
 * PhotoSection — Photo grid + add photo
 *
 * Location: apps/mobile/features/jobs/components/detail/PhotoSection.tsx
 *
 * MOB-B6: expo-image-picker installed. "+ Add Photo" is now functional.
 * Shows action sheet (iOS) or Alert (Android) to choose camera or library.
 * Photo URI written to WatermelonDB via useCreatePhoto hook (pending upload).
 *
 * Shows pending photos from WatermelonDB (localUri + uploadProgress).
 * Synced photos would show S3 URL (future enhancement).
 *
 * Per batch-mob-b6-design.md Step 5.
 * Per batch-mob-b2-design.md §F.10 and §G.4.
 */

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Pressable,
  Image,
  Alert,
  StyleSheet,
  FlatList,
  ActionSheetIOS,
  Platform,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import {
  colors,
  mobileFontSizes,
  fontWeights,
  spacing,
  radii,
} from "@pilot/ui/tokens";
import { database } from "../../../../database";
import { Q } from "@nozbe/watermelondb";
import type { Photo } from "../../../../database/models/Photo";
import { useCreatePhoto } from "../../../offline-sync/hooks/useCreatePhoto";

// ── Component ─────────────────────────────────────────────────────────────────

interface PhotoSectionProps {
  jobId: string;
  testID?: string;
}

interface PhotoRecord {
  id: string;
  localUri: string;
  uploadProgress: number;
  localSyncStatus: string;
}

export function PhotoSection({
  jobId,
  testID,
}: PhotoSectionProps): React.ReactElement {
  const [photos, setPhotos] = useState<PhotoRecord[]>([]);
  const { create: createPhoto } = useCreatePhoto();

  // Load photos for this job from WatermelonDB
  useEffect(() => {
    let cancelled = false;

    async function loadPhotos() {
      try {
        const records = await database
          .get<Photo>("photos")
          .query(Q.where("job_id", jobId))
          .fetch();

        if (!cancelled) {
          setPhotos(
            records.map((r) => ({
              id: r.id,
              localUri: r.localUri,
              uploadProgress: r.uploadProgress,
              localSyncStatus: r.localSyncStatus,
            })),
          );
        }
      } catch {
        // Database not ready — ignore
      }
    }

    void loadPhotos();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  // Reload photos after a new record is written
  const reloadPhotos = async () => {
    try {
      const records = await database
        .get<Photo>("photos")
        .query(Q.where("job_id", jobId))
        .fetch();
      setPhotos(
        records.map((r) => ({
          id: r.id,
          localUri: r.localUri,
          uploadProgress: r.uploadProgress,
          localSyncStatus: r.localSyncStatus,
        })),
      );
    } catch {
      // ignore
    }
  };

  const launchPicker = async (source: "camera" | "library") => {
    if (source === "camera") {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== "granted") {
        Alert.alert(
          "Camera permission required",
          "Please allow camera access in Settings.",
        );
        return;
      }
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: "images",
        quality: 0.8,
      });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        try {
          await createPhoto({
            jobId,
            localUri: asset.uri,
            mimeType: asset.mimeType ?? "image/jpeg",
            fileSizeBytes: asset.fileSize ?? 0,
          });
          await reloadPhotos();
        } catch (err) {
          console.error("[PhotoSection] Failed to create photo record:", err);
          Alert.alert("Error", "Failed to save photo. Please try again.");
        }
      }
    } else {
      const { status } =
        await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== "granted") {
        Alert.alert(
          "Photo library access required",
          "Please allow photo library access in Settings.",
        );
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: "images",
        quality: 0.8,
        allowsMultipleSelection: false,
      });
      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        try {
          await createPhoto({
            jobId,
            localUri: asset.uri,
            mimeType: asset.mimeType ?? "image/jpeg",
            fileSizeBytes: asset.fileSize ?? 0,
          });
          await reloadPhotos();
        } catch (err) {
          console.error("[PhotoSection] Failed to create photo record:", err);
          Alert.alert("Error", "Failed to save photo. Please try again.");
        }
      }
    }
  };

  const handleAddPhoto = () => {
    if (Platform.OS === "ios") {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options: ["Cancel", "Take Photo", "Choose from Library"],
          cancelButtonIndex: 0,
        },
        (buttonIndex) => {
          if (buttonIndex === 1) {
            void launchPicker("camera");
          } else if (buttonIndex === 2) {
            void launchPicker("library");
          }
        },
      );
    } else {
      Alert.alert("Add Photo", "Choose a source", [
        { text: "Cancel", style: "cancel" },
        { text: "Take Photo", onPress: () => void launchPicker("camera") },
        {
          text: "Choose from Library",
          onPress: () => void launchPicker("library"),
        },
      ]);
    }
  };

  return (
    <View style={styles.container} testID={testID ?? "photo-section"}>
      {/* Header row */}
      <View style={styles.headerRow}>
        <Text style={styles.sectionTitle}>PHOTOS</Text>
        <Pressable
          style={styles.addButton}
          onPress={handleAddPhoto}
          accessibilityRole="button"
          accessibilityLabel="Add photo"
          testID="add-photo-button"
        >
          <Text style={styles.addButtonText}>+ Add</Text>
        </Pressable>
      </View>

      {/* Photo grid */}
      {photos.length === 0 ? (
        <Text style={styles.emptyText}>No photos captured</Text>
      ) : (
        <FlatList
          data={photos}
          keyExtractor={(item) => item.id}
          numColumns={3}
          scrollEnabled={false}
          renderItem={({ item }) => (
            <View style={styles.photoTile} testID={`photo-tile-${item.id}`}>
              <Image
                source={{ uri: item.localUri }}
                style={styles.photoImage}
                accessibilityLabel="Job photo"
              />
              {/* Upload progress indicator for pending photos */}
              {item.localSyncStatus !== "synced" &&
                item.uploadProgress < 100 && (
                  <View style={styles.progressOverlay}>
                    <Text style={styles.progressText}>
                      {item.uploadProgress > 0
                        ? `${item.uploadProgress}%`
                        : "⏳"}
                    </Text>
                  </View>
                )}
            </View>
          )}
          columnWrapperStyle={styles.photoRow}
          ItemSeparatorComponent={() => <View style={{ height: spacing[2] }} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.neutral[800],
    borderRadius: radii.md,
    padding: spacing[4],
    marginBottom: spacing[3],
    gap: spacing[3],
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionTitle: {
    fontSize: mobileFontSizes.caption,
    fontWeight: String(fontWeights.medium) as "500",
    color: colors.neutral[400],
    textTransform: "uppercase",
    letterSpacing: 0.5,
    lineHeight: 16,
  },
  addButton: {
    paddingVertical: spacing[1],
    paddingHorizontal: spacing[2],
  },
  addButtonText: {
    fontSize: mobileFontSizes.body,
    color: colors.brand[400],
    lineHeight: 20,
  },
  emptyText: {
    fontSize: mobileFontSizes.body,
    color: colors.neutral[400],
    lineHeight: 20,
  },
  photoRow: {
    gap: spacing[2],
  },
  photoTile: {
    flex: 1,
    aspectRatio: 1,
    borderRadius: radii.sm,
    overflow: "hidden",
    backgroundColor: colors.neutral[600],
    position: "relative",
  },
  photoImage: {
    width: "100%",
    height: "100%",
  },
  progressOverlay: {
    position: "absolute",
    bottom: 2,
    right: 2,
    backgroundColor: "rgba(0,0,0,0.6)",
    borderRadius: radii.sm,
    paddingHorizontal: spacing[1],
    paddingVertical: 1,
  },
  progressText: {
    fontSize: mobileFontSizes.caption,
    color: colors.neutral[50],
    lineHeight: 14,
  },
});
