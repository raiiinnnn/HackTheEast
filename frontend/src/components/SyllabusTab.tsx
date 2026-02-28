import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { updateSyllabus, TopicInput } from "../api/courses";
import { CourseResponse } from "../api/types";

interface Props {
  course: CourseResponse;
  onRefresh: () => void;
}

export default function SyllabusTab({ course, onRefresh }: Props) {
  const [editing, setEditing] = useState(false);
  const [topics, setTopics] = useState<TopicInput[]>([]);
  const [saving, setSaving] = useState(false);

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
      Alert.alert("Error", "Add at least one topic with a title");
      return;
    }
    setSaving(true);
    try {
      await updateSyllabus(course.id, valid);
      setEditing(false);
      setTopics([]);
      onRefresh();
    } catch (e: any) {
      Alert.alert("Error", e.response?.data?.detail || "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {course.topics.length > 0 && (
        <View style={styles.existing}>
          {course.topics.map((topic) => (
            <View key={topic.id} style={styles.topicCard}>
              <Text style={styles.topicTitle}>{topic.title}</Text>
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

      {!editing ? (
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => setEditing(true)}
        >
          <Text style={styles.addBtnText}>+ Add Topics</Text>
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
  existing: { marginBottom: Spacing.lg },
  topicCard: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  topicTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
    marginBottom: Spacing.sm,
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
