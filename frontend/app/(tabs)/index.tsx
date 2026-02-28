import { useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { useFocusEffect, router } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../../src/constants/theme";
import { listCourses, createCourse } from "../../src/api/courses";
import { useAppStore } from "../../src/store/app";
import { CourseResponse } from "../../src/api/types";

export default function CoursesScreen() {
  const courses = useAppStore((s) => s.courses);
  const setCourses = useAppStore((s) => s.setCourses);
  const addCourse = useAppStore((s) => s.addCourse);

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");

  const fetchCourses = useCallback(async () => {
    try {
      const data = await listCourses();
      setCourses(data);
    } catch {
      // silent fail on refresh
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchCourses();
    }, [fetchCourses])
  );

  const handleCreate = async () => {
    if (!title.trim()) {
      Alert.alert("Error", "Course title is required");
      return;
    }
    setCreating(true);
    try {
      const course = await createCourse(title.trim(), desc.trim() || undefined);
      addCourse(course);
      setTitle("");
      setDesc("");
      setShowForm(false);
      router.push(`/course/${course.id}`);
    } catch (e: any) {
      Alert.alert("Error", e.response?.data?.detail || "Failed to create course");
    } finally {
      setCreating(false);
    }
  };

  const renderCourse = ({ item }: { item: CourseResponse }) => (
    <TouchableOpacity
      style={styles.card}
      onPress={() => router.push(`/course/${item.id}`)}
      activeOpacity={0.7}
    >
      <View style={styles.cardHeader}>
        <Text style={styles.cardEmoji}>📘</Text>
        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle}>{item.title}</Text>
          {item.description && (
            <Text style={styles.cardDesc} numberOfLines={2}>
              {item.description}
            </Text>
          )}
        </View>
      </View>
      <View style={styles.cardMeta}>
        <Text style={styles.metaText}>
          {item.topics?.length || 0} topics
        </Text>
        <Text style={styles.metaText}>→</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {showForm && (
        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Course title"
            placeholderTextColor={Colors.textMuted}
            value={title}
            onChangeText={setTitle}
          />
          <TextInput
            style={styles.input}
            placeholder="Description (optional)"
            placeholderTextColor={Colors.textMuted}
            value={desc}
            onChangeText={setDesc}
          />
          <View style={styles.formActions}>
            <TouchableOpacity
              style={styles.cancelBtn}
              onPress={() => setShowForm(false)}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.createBtn, creating && { opacity: 0.6 }]}
              onPress={handleCreate}
              disabled={creating}
            >
              {creating ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.createText}>Create</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}

      <FlatList
        data={courses}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderCourse}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={fetchCourses} tintColor={Colors.primary} />
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>📖</Text>
            <Text style={styles.emptyTitle}>No courses yet</Text>
            <Text style={styles.emptyDesc}>
              Create your first course to start learning
            </Text>
          </View>
        }
      />

      {!showForm && (
        <TouchableOpacity
          style={styles.fab}
          onPress={() => setShowForm(true)}
        >
          <Text style={styles.fabText}>+</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
  },
  list: { padding: Spacing.md, paddingBottom: 100 },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cardHeader: { flexDirection: "row", alignItems: "flex-start", gap: Spacing.md },
  cardEmoji: { fontSize: 32 },
  cardInfo: { flex: 1 },
  cardTitle: { color: Colors.text, fontSize: FontSize.lg, fontWeight: "700" },
  cardDesc: { color: Colors.textSecondary, fontSize: FontSize.sm, marginTop: 4 },
  cardMeta: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: Spacing.md,
    paddingTop: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  metaText: { color: Colors.textMuted, fontSize: FontSize.sm },
  form: {
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: Spacing.sm,
  },
  input: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    fontSize: FontSize.md,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  formActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: Spacing.sm,
    marginTop: Spacing.xs,
  },
  cancelBtn: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
  },
  cancelText: { color: Colors.textSecondary, fontSize: FontSize.md },
  createBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
  },
  createText: { color: Colors.text, fontSize: FontSize.md, fontWeight: "600" },
  fab: {
    position: "absolute",
    bottom: 30,
    right: 20,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 8,
  },
  fabText: { color: "#fff", fontSize: 28, fontWeight: "600", marginTop: -2 },
  empty: { alignItems: "center", marginTop: 80 },
  emptyEmoji: { fontSize: 60, marginBottom: Spacing.md },
  emptyTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  emptyDesc: { color: Colors.textSecondary, fontSize: FontSize.md },
});
