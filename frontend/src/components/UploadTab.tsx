import { useState, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Platform,
  ScrollView,
} from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { uploadMaterial } from "../api/uploads";
import { generateContent } from "../api/generate";
import { CourseResponse } from "../api/types";

const ACCEPTED_MIME =
  "application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation,video/mp4,video/quicktime";

interface UploadedFile {
  name: string;
  status: "uploading" | "done" | "error";
  error?: string;
}

interface Props {
  courseId: number;
  course: CourseResponse;
}

export default function UploadTab({ courseId, course }: Props) {
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const showAlert = (title: string, message: string) => {
    if (Platform.OS === "web") {
      window.alert(`${title}\n\n${message}`);
    } else {
      Alert.alert(title, message);
    }
  };

  const doUploadSingle = async (
    fileOrUri: File | string,
    fileName: string,
    mimeType: string
  ): Promise<boolean> => {
    try {
      await uploadMaterial(courseId, fileOrUri, fileName, mimeType);
      return true;
    } catch (e: any) {
      throw new Error(e.response?.data?.detail || "Upload failed");
    }
  };

  const handlePickNative = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: [
          "application/pdf",
          "application/vnd.openxmlformats-officedocument.presentationml.presentation",
          "video/mp4",
          "video/quicktime",
        ],
        copyToCacheDirectory: true,
        multiple: true,
      });
      if (result.canceled || !result.assets?.length) return;

      setUploading(true);
      for (const file of result.assets) {
        const entry: UploadedFile = { name: file.name, status: "uploading" };
        setUploadedFiles((prev) => [...prev, entry]);
        try {
          await doUploadSingle(
            file.uri,
            file.name,
            file.mimeType || "application/octet-stream"
          );
          setUploadedFiles((prev) =>
            prev.map((f) => (f.name === file.name && f.status === "uploading" ? { ...f, status: "done" } : f))
          );
        } catch (e: any) {
          setUploadedFiles((prev) =>
            prev.map((f) =>
              f.name === file.name && f.status === "uploading"
                ? { ...f, status: "error", error: e.message }
                : f
            )
          );
        }
      }
      setUploading(false);
    } catch {
      showAlert("Error", "Could not open document picker");
    }
  };

  const handlePickWeb = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleWebFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const entry: UploadedFile = { name: file.name, status: "uploading" };
      setUploadedFiles((prev) => [...prev, entry]);
      try {
        await doUploadSingle(file, file.name, file.type || "application/octet-stream");
        setUploadedFiles((prev) =>
          prev.map((f) => (f.name === file.name && f.status === "uploading" ? { ...f, status: "done" } : f))
        );
      } catch (err: any) {
        setUploadedFiles((prev) =>
          prev.map((f) =>
            f.name === file.name && f.status === "uploading"
              ? { ...f, status: "error", error: err.message }
              : f
          )
        );
      }
    }
    setUploading(false);
  };

  const handlePick = Platform.OS === "web" ? handlePickWeb : handlePickNative;

  const doneCount = uploadedFiles.filter((f) => f.status === "done").length;

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await generateContent(courseId);
      showAlert(
        "Content Generated",
        `Created ${res.reels_created} reels, ${res.concept_cards_created} concept cards, and ${res.quiz_items_created} quiz items.\n\nSwitch to the Feed tab to start learning!`
      );
    } catch (e: any) {
      showAlert(
        "Generation failed",
        e.response?.data?.detail || "Make sure you've uploaded materials first"
      );
    } finally {
      setGenerating(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {Platform.OS === "web" && (
        <input
          ref={fileInputRef as any}
          type="file"
          accept={ACCEPTED_MIME}
          multiple
          style={{ display: "none" }}
          onChange={handleWebFileChange as any}
        />
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Upload Materials</Text>
        <Text style={styles.sectionDesc}>
          Upload PDFs, PowerPoint slides, or lecture videos. You can select
          multiple files at once. The AI will extract key concepts and generate
          learning content.
        </Text>

        <TouchableOpacity
          style={[styles.uploadBtn, uploading && { opacity: 0.6 }]}
          onPress={handlePick}
          disabled={uploading}
        >
          {uploading ? (
            <View style={styles.uploadingRow}>
              <ActivityIndicator color={Colors.primary} />
              <Text style={styles.uploadingText}>Uploading...</Text>
            </View>
          ) : (
            <>
              <Text style={styles.uploadIcon}>📁</Text>
              <Text style={styles.uploadText}>
                Choose Files
              </Text>
              <Text style={styles.uploadHint}>PDF, PPTX, or MP4 — select multiple</Text>
            </>
          )}
        </TouchableOpacity>

        {uploadedFiles.length > 0 && (
          <View style={styles.fileList}>
            <Text style={styles.fileListTitle}>
              Uploaded ({doneCount}/{uploadedFiles.length})
            </Text>
            {uploadedFiles.map((f, idx) => (
              <View key={`${f.name}-${idx}`} style={styles.fileRow}>
                <Text style={styles.fileIcon}>
                  {f.status === "done" ? "✅" : f.status === "uploading" ? "⏳" : "❌"}
                </Text>
                <Text
                  style={[
                    styles.fileName,
                    f.status === "error" && { color: Colors.error },
                  ]}
                  numberOfLines={1}
                >
                  {f.name}
                </Text>
                {f.error && (
                  <Text style={styles.fileError} numberOfLines={1}>
                    {f.error}
                  </Text>
                )}
              </View>
            ))}
          </View>
        )}
      </View>

      <View style={styles.divider} />

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Generate Learning Content</Text>
        <Text style={styles.sectionDesc}>
          After uploading materials, generate reels, concept cards, and quizzes
          using AI. All uploaded files for this course will be used.
        </Text>

        <TouchableOpacity
          style={[styles.generateBtn, generating && { opacity: 0.6 }]}
          onPress={handleGenerate}
          disabled={generating}
        >
          {generating ? (
            <View style={styles.genLoading}>
              <ActivityIndicator color="#fff" />
              <Text style={styles.genLoadingText}>Generating with MiniMax AI...</Text>
            </View>
          ) : (
            <Text style={styles.generateText}>Generate Focus Feed</Text>
          )}
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  contentContainer: { padding: Spacing.md, paddingBottom: 40 },
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
  uploadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
  },
  uploadingText: { color: Colors.primary, fontSize: FontSize.md, fontWeight: "600" },
  fileList: {
    marginTop: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  fileListTitle: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    fontWeight: "600",
    marginBottom: Spacing.sm,
  },
  fileRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 6,
    gap: Spacing.sm,
  },
  fileIcon: { fontSize: 14 },
  fileName: {
    color: Colors.text,
    fontSize: FontSize.sm,
    flex: 1,
  },
  fileError: {
    color: Colors.error,
    fontSize: FontSize.xs,
    maxWidth: 150,
  },
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
