import { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { uploadMaterial } from "../api/uploads";
import { generateContent } from "../api/generate";
import { CourseResponse } from "../api/types";

interface Props {
  courseId: number;
  course: CourseResponse;
}

export default function UploadTab({ courseId, course }: Props) {
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [lastUpload, setLastUpload] = useState<string | null>(null);

  const handlePick = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          "application/pdf",
          "application/vnd.openxmlformats-officedocument.presentationml.presentation",
          "video/mp4",
          "video/quicktime",
        ],
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets?.[0]) return;

      const file = result.assets[0];
      setUploading(true);
      try {
        const res = await uploadMaterial(
          courseId,
          file.uri,
          file.name,
          file.mimeType || "application/octet-stream"
        );
        setLastUpload(res.filename);
        Alert.alert("Uploaded", `${res.filename} uploaded successfully`);
      } catch (e: any) {
        Alert.alert("Upload failed", e.response?.data?.detail || "Try again");
      } finally {
        setUploading(false);
      }
    } catch {
      Alert.alert("Error", "Could not open document picker");
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await generateContent(courseId);
      Alert.alert(
        "Content Generated",
        `Created ${res.reels_created} reels, ${res.concept_cards_created} concept cards, and ${res.quiz_items_created} quiz items.\n\nSwitch to the Feed tab to start learning!`
      );
    } catch (e: any) {
      Alert.alert(
        "Generation failed",
        e.response?.data?.detail || "Make sure you've uploaded materials first"
      );
    } finally {
      setGenerating(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Upload Materials</Text>
        <Text style={styles.sectionDesc}>
          Upload PDFs, PowerPoint slides, or lecture videos. The AI will extract
          key concepts and generate learning content.
        </Text>

        <TouchableOpacity
          style={[styles.uploadBtn, uploading && { opacity: 0.6 }]}
          onPress={handlePick}
          disabled={uploading}
        >
          {uploading ? (
            <ActivityIndicator color={Colors.primary} />
          ) : (
            <>
              <Text style={styles.uploadIcon}>📁</Text>
              <Text style={styles.uploadText}>Choose File</Text>
              <Text style={styles.uploadHint}>PDF, PPTX, or MP4</Text>
            </>
          )}
        </TouchableOpacity>

        {lastUpload && (
          <View style={styles.lastFile}>
            <Text style={styles.lastFileText}>Last uploaded: {lastUpload}</Text>
          </View>
        )}
      </View>

      <View style={styles.divider} />

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Generate Learning Content</Text>
        <Text style={styles.sectionDesc}>
          After uploading materials, generate reels, concept cards, and quizzes
          using AI.
        </Text>

        <TouchableOpacity
          style={[styles.generateBtn, generating && { opacity: 0.6 }]}
          onPress={handleGenerate}
          disabled={generating}
        >
          {generating ? (
            <View style={styles.genLoading}>
              <ActivityIndicator color="#fff" />
              <Text style={styles.genLoadingText}>Generating...</Text>
            </View>
          ) : (
            <Text style={styles.generateText}>Generate Focus Feed</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: Spacing.md },
  section: { marginBottom: Spacing.lg },
  sectionTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  sectionDesc: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    marginBottom: Spacing.md,
    lineHeight: 20,
  },
  uploadBtn: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.xl,
    alignItems: "center",
    borderWidth: 2,
    borderColor: Colors.border,
    borderStyle: "dashed",
  },
  uploadIcon: { fontSize: 36, marginBottom: Spacing.sm },
  uploadText: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: "600",
    marginBottom: 4,
  },
  uploadHint: { color: Colors.textMuted, fontSize: FontSize.sm },
  lastFile: {
    marginTop: Spacing.sm,
    padding: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.sm,
  },
  lastFileText: { color: Colors.success, fontSize: FontSize.sm },
  divider: {
    height: 1,
    backgroundColor: Colors.border,
    marginVertical: Spacing.md,
  },
  generateBtn: {
    backgroundColor: Colors.primary,
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.md,
    alignItems: "center",
  },
  generateText: { color: "#fff", fontSize: FontSize.lg, fontWeight: "700" },
  genLoading: { flexDirection: "row", alignItems: "center", gap: Spacing.sm },
  genLoadingText: { color: "#fff", fontSize: FontSize.md },
});
