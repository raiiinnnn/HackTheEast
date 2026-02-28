import { useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useFocusEffect } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { getCourseProgress } from "../api/progress";
import { updateCadence } from "../api/progress";
import { CourseProgressResponse, SubtopicProgressResponse } from "../api/types";

interface Props {
  courseId: number;
}

export default function ProgressTab({ courseId }: Props) {
  const [progress, setProgress] = useState<CourseProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProgress = useCallback(async () => {
    try {
      const data = await getCourseProgress(courseId);
      setProgress(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useFocusEffect(
    useCallback(() => {
      fetchProgress();
    }, [fetchProgress])
  );

  const handleCadence = async (
    subtopicId: number,
    cadence: string
  ) => {
    try {
      await updateCadence(subtopicId, cadence);
      fetchProgress();
    } catch {}
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (!progress || progress.subtopics.length === 0) {
    return (
      <View style={styles.center}>
        <Text style={styles.emptyIcon}>📊</Text>
        <Text style={styles.emptyTitle}>No progress yet</Text>
        <Text style={styles.emptyDesc}>
          Complete reels and quizzes to track your mastery
        </Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.overallCard}>
        <Text style={styles.overallLabel}>Overall Mastery</Text>
        <Text style={styles.overallScore}>
          {Math.round(progress.overall_mastery)}%
        </Text>
        <View style={styles.overallBar}>
          <View
            style={[
              styles.overallBarFill,
              { width: `${Math.min(progress.overall_mastery, 100)}%` },
            ]}
          />
        </View>
      </View>

      {progress.subtopics.map((sub) => (
        <SubtopicCard
          key={sub.subtopic_id}
          item={sub}
          onCadenceChange={(c) => handleCadence(sub.subtopic_id, c)}
        />
      ))}
    </ScrollView>
  );
}

function SubtopicCard({
  item,
  onCadenceChange,
}: {
  item: SubtopicProgressResponse;
  onCadenceChange: (cadence: string) => void;
}) {
  const masteryColor =
    item.mastery_score >= 70
      ? Colors.success
      : item.mastery_score >= 40
      ? Colors.warning
      : Colors.error;

  return (
    <View style={styles.subtopicCard}>
      <View style={styles.subtopicHeader}>
        <View style={{ flex: 1 }}>
          <Text style={styles.subtopicTopic}>{item.topic_title}</Text>
          <Text style={styles.subtopicTitle}>{item.subtopic_title}</Text>
        </View>
        <Text style={[styles.subtopicScore, { color: masteryColor }]}>
          {Math.round(item.mastery_score)}%
        </Text>
      </View>

      <View style={styles.progressBar}>
        <View
          style={[
            styles.progressBarFill,
            {
              width: `${Math.min(item.mastery_score, 100)}%`,
              backgroundColor: masteryColor,
            },
          ]}
        />
      </View>

      <View style={styles.stats}>
        <Text style={styles.stat}>
          {item.reels_watched} reels watched
        </Text>
        <Text style={styles.stat}>
          {item.correct_attempts}/{item.total_attempts} correct
        </Text>
      </View>

      <View style={styles.cadence}>
        <Text style={styles.cadenceLabel}>Review:</Text>
        {["daily", "weekly"].map((c) => (
          <TouchableOpacity
            key={c}
            style={[
              styles.cadenceBtn,
              item.review_cadence === c && styles.cadenceBtnActive,
            ]}
            onPress={() => onCadenceChange(c)}
          >
            <Text
              style={[
                styles.cadenceText,
                item.review_cadence === c && styles.cadenceTextActive,
              ]}
            >
              {c}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: Spacing.md, paddingBottom: 40 },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: Spacing.xl,
  },
  emptyIcon: { fontSize: 60, marginBottom: Spacing.md },
  emptyTitle: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  emptyDesc: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    textAlign: "center",
  },
  overallCard: {
    backgroundColor: Colors.primary,
    borderRadius: BorderRadius.xl,
    padding: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  overallLabel: {
    color: "rgba(255,255,255,0.8)",
    fontSize: FontSize.sm,
    fontWeight: "600",
  },
  overallScore: {
    color: "#fff",
    fontSize: FontSize.hero,
    fontWeight: "800",
    marginVertical: Spacing.xs,
  },
  overallBar: {
    height: 8,
    backgroundColor: "rgba(255,255,255,0.2)",
    borderRadius: 4,
    overflow: "hidden",
  },
  overallBarFill: {
    height: "100%",
    backgroundColor: "#fff",
    borderRadius: 4,
  },
  subtopicCard: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  subtopicHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: Spacing.sm,
  },
  subtopicTopic: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    marginBottom: 2,
  },
  subtopicTitle: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: "600",
  },
  subtopicScore: {
    fontSize: FontSize.xl,
    fontWeight: "800",
  },
  progressBar: {
    height: 6,
    backgroundColor: Colors.surfaceLight,
    borderRadius: 3,
    overflow: "hidden",
    marginBottom: Spacing.sm,
  },
  progressBarFill: {
    height: "100%",
    borderRadius: 3,
  },
  stats: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: Spacing.sm,
  },
  stat: { color: Colors.textMuted, fontSize: FontSize.xs },
  cadence: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    paddingTop: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  cadenceLabel: { color: Colors.textSecondary, fontSize: FontSize.sm },
  cadenceBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.surfaceLight,
  },
  cadenceBtnActive: { backgroundColor: Colors.primary },
  cadenceText: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    fontWeight: "600",
    textTransform: "capitalize",
  },
  cadenceTextActive: { color: "#fff" },
});
