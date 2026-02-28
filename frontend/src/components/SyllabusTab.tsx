import { useState, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
  Platform,
} from "react-native";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import {
  updateSyllabus,
  deleteTopic,
  TopicInput,
  parseSyllabusPdf,
  ParsedSyllabusResponse,
} from "../api/courses";
import { CourseResponse } from "../api/types";

interface Props {
  course: CourseResponse;
  onRefresh: () => void;
}

export default function SyllabusTab({ course, onRefresh }: Props) {
  const [editing, setEditing] = useState(false);
  const [topics, setTopics] = useState<TopicInput[]>([]);
  const [saving, setSaving] = useState(false);

  const [deletingId, setDeletingId] = useState<number | null>(null);

  const [parsing, setParsing] = useState(false);
  const [parsed, setParsed] = useState<ParsedSyllabusResponse | null>(null);
  const [savingParsed, setSavingParsed] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const showAlert = (title: string, message: string) => {
    if (Platform.OS === "web") {
      window.alert(`${title}\n\n${message}`);
    } else {
      Alert.alert(title, message);
    }
  };

  const handleDeleteTopic = async (topicId: number) => {
    if (Platform.OS === "web") {
      if (!window.confirm("Delete this topic and all its subtopics?")) return;
    }
    setDeletingId(topicId);
    try {
      await deleteTopic(course.id, topicId);
      onRefresh();
    } catch (e: any) {
      showAlert("Error", e.response?.data?.detail || "Failed to delete topic");
    } finally {
      setDeletingId(null);
    }
  };

  // --- PDF upload & parse ---
  const handleUploadPress = () => {
    if (Platform.OS === "web" && fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleFileSelected = async (file: File) => {
    if (!file.type.includes("pdf")) {
      showAlert("Invalid file", "Please select a PDF file");
      return;
    }
    setParsing(true);
    setParsed(null);
    try {
      const result = await parseSyllabusPdf(file, course.title);
      setParsed(result);
    } catch (e: any) {
      showAlert(
        "Parse failed",
        e.response?.data?.detail || "Could not parse syllabus PDF"
      );
    } finally {
      setParsing(false);
    }
  };

  const handleWebFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelected(file);
  };

  const handleSaveParsed = async () => {
    if (!parsed) return;
    setSavingParsed(true);
    try {
      const topicsPayload: TopicInput[] = parsed.topics.map((t, i) => ({
        title: t.topic,
        order: i,
        subtopics: t.subtopics.map((s, j) => ({ title: s, order: j })),
      }));
      await updateSyllabus(course.id, topicsPayload);
      setParsed(null);
      onRefresh();
      showAlert("Saved", "Syllabus structure has been saved to your course");
    } catch (e: any) {
      showAlert("Save failed", e.response?.data?.detail || "Could not save");
    } finally {
      setSavingParsed(false);
    }
  };

  // --- Manual editing ---
  const addTopic = () => {
    setTopics([
      ...topics,
      { title: "", order: topics.length, subtopics: [] },
    ]);
  };

  const addSubtopic = (topicIdx: number) => {
    const updated = [...topics];
    updated[topicIdx].subtopics.push({
      title: "",
      order: updated[topicIdx].subtopics.length,
    });
    setTopics(updated);
  };

  const updateTopicTitle = (idx: number, title: string) => {
    const updated = [...topics];
    updated[idx].title = title;
    setTopics(updated);
  };

  const updateSubtopicTitle = (
    topicIdx: number,
    subIdx: number,
    title: string
  ) => {
    const updated = [...topics];
    updated[topicIdx].subtopics[subIdx].title = title;
    setTopics(updated);
  };

  const handleSave = async () => {
    const valid = topics.filter((t) => t.title.trim());
    if (!valid.length) {
      showAlert("Error", "Add at least one topic with a title");
      return;
    }
    setSaving(true);
    try {
      await updateSyllabus(course.id, valid);
      setEditing(false);
      setTopics([]);
      onRefresh();
    } catch (e: any) {
      showAlert("Error", e.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Hidden file input for web */}
      {Platform.OS === "web" && (
        <input
          ref={fileInputRef as any}
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={handleWebFileChange as any}
        />
      )}

      {/* Upload syllabus PDF section */}
      <View style={styles.uploadSection}>
        <Text style={styles.uploadTitle}>Import from PDF</Text>
        <Text style={styles.uploadDesc}>
          Upload your course syllabus PDF and AI will automatically extract
          topics and subtopics.
        </Text>
        <TouchableOpacity
          style={[styles.uploadBtn, parsing && { opacity: 0.6 }]}
          onPress={handleUploadPress}
          disabled={parsing}
        >
          {parsing ? (
            <View style={styles.parsingRow}>
              <ActivityIndicator color={Colors.secondary} />
              <Text style={styles.parsingText}>Analyzing syllabus...</Text>
            </View>
          ) : (
            <>
              <Text style={styles.uploadIcon}>📄</Text>
              <Text style={styles.uploadBtnText}>Upload Syllabus PDF</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Parsed result preview */}
      {parsed && (
        <View style={styles.parsedSection}>
          <View style={styles.parsedHeader}>
            <Text style={styles.parsedTitle}>
              Extracted: {parsed.course_name}
            </Text>
            <Text style={styles.parsedCount}>
              {parsed.topics.length} topics found
            </Text>
          </View>

          {parsed.topics.map((t, idx) => (
            <View key={idx} style={styles.parsedTopicCard}>
              <View style={styles.parsedTopicHeader}>
                <Text style={styles.parsedTopicName}>{t.topic}</Text>
                {t.weight > 0 && (
                  <View style={styles.weightBadge}>
                    <Text style={styles.weightText}>
                      {Math.round(t.weight * 100)}%
                    </Text>
                  </View>
                )}
              </View>
              {t.subtopics.map((s, sIdx) => (
                <View key={sIdx} style={styles.parsedSubtopic}>
                  <View style={styles.bullet} />
                  <Text style={styles.parsedSubtopicText}>{s}</Text>
                </View>
              ))}
            </View>
          ))}

          <View style={styles.parsedActions}>
            <TouchableOpacity
              onPress={() => setParsed(null)}
              style={styles.discardBtn}
            >
              <Text style={styles.discardText}>Discard</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.saveParsedBtn, savingParsed && { opacity: 0.6 }]}
              onPress={handleSaveParsed}
              disabled={savingParsed}
            >
              {savingParsed ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.saveParsedText}>Save to Course</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* Divider */}
      {(course.topics.length > 0 || !parsed) && (
        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>or add manually</Text>
          <View style={styles.dividerLine} />
        </View>
      )}

      {/* Existing topics */}
      {course.topics.length > 0 && (
        <View style={styles.existing}>
          {course.topics.map((topic) => (
            <View key={topic.id} style={styles.topicCard}>
              <View style={styles.topicHeader}>
                <Text style={[styles.topicTitle, { flex: 1, marginBottom: 0 }]}>
                  {topic.title}
                </Text>
                <TouchableOpacity
                  style={styles.deleteBtn}
                  onPress={() => handleDeleteTopic(topic.id)}
                  disabled={deletingId === topic.id}
                >
                  {deletingId === topic.id ? (
                    <ActivityIndicator color={Colors.error} size="small" />
                  ) : (
                    <Text style={styles.deleteText}>✕</Text>
                  )}
                </TouchableOpacity>
              </View>
              {topic.subtopics.map((sub) => (
                <View key={sub.id} style={styles.subtopic}>
                  <View style={styles.bullet} />
                  <Text style={styles.subtopicText}>{sub.title}</Text>
                </View>
              ))}
            </View>
          ))}
        </View>
      )}

      {/* Manual editor */}
      {!editing ? (
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setEditing(true)}
        >
          <Text style={styles.addBtnText}>+ Add Topics Manually</Text>
        </TouchableOpacity>
      ) : (
        <View style={styles.editor}>
          <Text style={styles.editorTitle}>Add Syllabus</Text>
          {topics.map((topic, tIdx) => (
            <View key={tIdx} style={styles.editTopicCard}>
              <TextInput
                style={styles.topicInput}
                placeholder={`Topic ${tIdx + 1}`}
                placeholderTextColor={Colors.textMuted}
                value={topic.title}
                onChangeText={(t) => updateTopicTitle(tIdx, t)}
              />
              {topic.subtopics.map((sub, sIdx) => (
                <TextInput
                  key={sIdx}
                  style={styles.subtopicInput}
                  placeholder={`Subtopic ${sIdx + 1}`}
                  placeholderTextColor={Colors.textMuted}
                  value={sub.title}
                  onChangeText={(t) => updateSubtopicTitle(tIdx, sIdx, t)}
                />
              ))}
              <TouchableOpacity
                style={styles.addSubBtn}
                onPress={() => addSubtopic(tIdx)}
              >
                <Text style={styles.addSubText}>+ Subtopic</Text>
              </TouchableOpacity>
            </View>
          ))}
          <TouchableOpacity style={styles.addTopicBtn} onPress={addTopic}>
            <Text style={styles.addTopicText}>+ Add Topic</Text>
          </TouchableOpacity>
          <View style={styles.editorActions}>
            <TouchableOpacity
              onPress={() => {
                setEditing(false);
                setTopics([]);
              }}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.saveBtn, saving && { opacity: 0.6 }]}
              onPress={handleSave}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.saveText}>Save</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  contentContainer: { padding: Spacing.md, paddingBottom: 40 },

  // Upload section
  uploadSection: { marginBottom: Spacing.md },
  uploadTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  uploadDesc: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    marginBottom: Spacing.md,
    lineHeight: 20,
  },
  uploadBtn: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    alignItems: "center",
    borderWidth: 2,
    borderColor: Colors.secondary,
    borderStyle: "dashed",
    flexDirection: "row",
    justifyContent: "center",
    gap: Spacing.sm,
  },
  uploadIcon: { fontSize: 24 },
  uploadBtnText: {
    color: Colors.secondary,
    fontSize: FontSize.md,
    fontWeight: "700",
  },
  parsingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
  },
  parsingText: {
    color: Colors.secondary,
    fontSize: FontSize.md,
    fontWeight: "600",
  },

  // Parsed preview
  parsedSection: {
    marginBottom: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.secondary,
  },
  parsedHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  parsedTitle: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: "700",
    flex: 1,
  },
  parsedCount: {
    color: Colors.secondary,
    fontSize: FontSize.sm,
    fontWeight: "600",
  },
  parsedTopicCard: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
  },
  parsedTopicHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.sm,
  },
  parsedTopicName: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: "700",
    flex: 1,
  },
  weightBadge: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.full,
  },
  weightText: {
    color: "#fff",
    fontSize: FontSize.xs,
    fontWeight: "700",
  },
  parsedSubtopic: {
    flexDirection: "row",
    alignItems: "center",
    paddingLeft: Spacing.sm,
    marginBottom: 4,
  },
  parsedSubtopicText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  parsedActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: Spacing.md,
    marginTop: Spacing.md,
    alignItems: "center",
  },
  discardBtn: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
  },
  discardText: { color: Colors.textMuted, fontSize: FontSize.md },
  saveParsedBtn: {
    backgroundColor: Colors.secondary,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
  },
  saveParsedText: { color: "#fff", fontSize: FontSize.md, fontWeight: "700" },

  // Divider
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: Spacing.lg,
    gap: Spacing.sm,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.border,
  },
  dividerText: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
  },

  // Existing topics
  existing: { marginBottom: Spacing.lg },
  topicCard: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  topicHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: Spacing.sm,
  },
  topicTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
    marginBottom: Spacing.sm,
  },
  deleteBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(255,107,107,0.15)",
    justifyContent: "center",
    alignItems: "center",
    marginLeft: Spacing.sm,
  },
  deleteText: {
    color: Colors.error,
    fontSize: FontSize.md,
    fontWeight: "700",
  },
  subtopic: {
    flexDirection: "row",
    alignItems: "center",
    paddingLeft: Spacing.md,
    marginBottom: 6,
  },
  bullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.primary,
    marginRight: Spacing.sm,
  },
  subtopicText: { color: Colors.textSecondary, fontSize: FontSize.md },

  // Manual editor
  addBtn: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
    borderStyle: "dashed",
  },
  addBtnText: { color: Colors.primary, fontSize: FontSize.md, fontWeight: "600" },
  editor: { gap: Spacing.md },
  editorTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
  },
  editTopicCard: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    gap: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  topicInput: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    fontSize: FontSize.md,
    color: Colors.text,
    fontWeight: "600",
  },
  subtopicInput: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    marginLeft: Spacing.md,
  },
  addSubBtn: { marginLeft: Spacing.md },
  addSubText: { color: Colors.secondary, fontSize: FontSize.sm },
  addTopicBtn: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderStyle: "dashed",
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    alignItems: "center",
  },
  addTopicText: { color: Colors.primary, fontSize: FontSize.md },
  editorActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: Spacing.md,
    alignItems: "center",
  },
  cancelText: { color: Colors.textSecondary, fontSize: FontSize.md },
  saveBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
  },
  saveText: { color: "#fff", fontSize: FontSize.md, fontWeight: "600" },
});
