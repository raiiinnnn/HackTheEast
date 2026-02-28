import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../../src/constants/theme";
import { getCourse } from "../../src/api/courses";
import { CourseResponse } from "../../src/api/types";
import SyllabusTab from "../../src/components/SyllabusTab";
import UploadTab from "../../src/components/UploadTab";
import FeedTab from "../../src/components/FeedTab";
import ProgressTab from "../../src/components/ProgressTab";

type TabName = "syllabus" | "upload" | "feed" | "progress";

const TABS: { key: TabName; label: string; icon: string }[] = [
  { key: "syllabus", label: "Syllabus", icon: "📋" },
  { key: "upload", label: "Upload", icon: "📎" },
  { key: "feed", label: "Feed", icon: "🎬" },
  { key: "progress", label: "Progress", icon: "📊" },
];

export default function CourseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const courseId = parseInt(id || "0", 10);

  const [course, setCourse] = useState<CourseResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabName>("syllabus");

  const fetchCourse = useCallback(async () => {
    try {
      const data = await getCourse(courseId);
      setCourse(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    fetchCourse();
  }, [fetchCourse]);

  if (loading || !course) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>{course.title}</Text>
        {course.description && (
          <Text style={styles.desc}>{course.description}</Text>
        )}
      </View>

      <View style={styles.tabs}>
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={styles.tabIcon}>{tab.icon}</Text>
            <Text
              style={[
                styles.tabLabel,
                activeTab === tab.key && styles.tabLabelActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.content}>
        {activeTab === "syllabus" && (
          <SyllabusTab course={course} onRefresh={fetchCourse} />
        )}
        {activeTab === "upload" && (
          <UploadTab courseId={courseId} course={course} />
        )}
        {activeTab === "feed" && <FeedTab courseId={courseId} />}
        {activeTab === "progress" && <ProgressTab courseId={courseId} />}
      </View>
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
  header: {
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.sm,
    paddingBottom: Spacing.md,
  },
  title: { color: Colors.text, fontSize: FontSize.xl, fontWeight: "800" },
  desc: { color: Colors.textSecondary, fontSize: FontSize.sm, marginTop: 4 },
  tabs: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    paddingHorizontal: Spacing.sm,
  },
  tab: {
    flex: 1,
    alignItems: "center",
    paddingVertical: Spacing.sm,
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabActive: { borderBottomColor: Colors.primary },
  tabIcon: { fontSize: 18, marginBottom: 2 },
  tabLabel: { color: Colors.textMuted, fontSize: FontSize.xs, fontWeight: "600" },
  tabLabelActive: { color: Colors.primary },
  content: { flex: 1 },
});
