import { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { QuizItemResponse } from "../api/types";

interface Props {
  quiz: QuizItemResponse;
  onAnswer: (answer: string) => Promise<any>;
}

export default function QuizCard({ quiz, onAnswer }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<{
    is_correct: boolean;
    correct_answer: string;
    explanation?: string;
  } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSelect = async (option: string) => {
    if (result) return;
    setSelected(option);
    setSubmitting(true);
    try {
      const res = await onAnswer(option);
      if (res) {
        setResult(res);
      } else {
        setResult({
          is_correct: false,
          correct_answer: "Unknown",
          explanation: "Could not verify answer",
        });
      }
    } catch {
      setResult({
        is_correct: false,
        correct_answer: "Unknown",
        explanation: "Network error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getOptionStyle = (option: string) => {
    if (!result) {
      return option === selected ? styles.optionSelected : styles.option;
    }
    if (option === result.correct_answer) return styles.optionCorrect;
    if (option === selected && !result.is_correct) return styles.optionWrong;
    return styles.option;
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>QUIZ</Text>
        </View>
        <Text style={styles.difficulty}>{quiz.difficulty}</Text>
      </View>

      <Text style={styles.question}>{quiz.question}</Text>

      <View style={styles.options}>
        {quiz.options?.map((option, idx) => (
          <TouchableOpacity
            key={idx}
            style={getOptionStyle(option)}
            onPress={() => handleSelect(option)}
            disabled={!!result || submitting}
            activeOpacity={0.7}
          >
            <View style={styles.optionLabel}>
              <Text style={styles.optionLetter}>
                {String.fromCharCode(65 + idx)}
              </Text>
            </View>
            <Text style={styles.optionText}>{option}</Text>
            {submitting && option === selected && (
              <ActivityIndicator
                size="small"
                color={Colors.primary}
                style={styles.optionLoader}
              />
            )}
          </TouchableOpacity>
        ))}
      </View>

      {result && (
        <View
          style={[
            styles.feedback,
            result.is_correct ? styles.feedbackCorrect : styles.feedbackWrong,
          ]}
        >
          <Text style={styles.feedbackTitle}>
            {result.is_correct ? "Correct! 🎉" : "Not quite 😅"}
          </Text>
          {result.explanation && (
            <Text style={styles.feedbackText}>{result.explanation}</Text>
          )}
          {!result.is_correct && (
            <Text style={styles.feedbackAnswer}>
              Answer: {result.correct_answer}
            </Text>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.card,
    borderRadius: BorderRadius.xl,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: Spacing.lg,
  },
  badge: {
    backgroundColor: Colors.accent,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
  badgeText: {
    color: "#fff",
    fontSize: FontSize.xs,
    fontWeight: "800",
    letterSpacing: 1,
  },
  difficulty: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    textTransform: "capitalize",
  },
  question: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "600",
    lineHeight: 28,
    marginBottom: Spacing.lg,
  },
  options: { gap: Spacing.sm },
  option: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  optionSelected: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 2,
    borderColor: Colors.primary,
  },
  optionCorrect: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(0,184,148,0.15)",
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 2,
    borderColor: Colors.success,
  },
  optionWrong: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,107,107,0.15)",
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 2,
    borderColor: Colors.error,
  },
  optionLabel: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginRight: Spacing.md,
  },
  optionLetter: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    fontWeight: "700",
  },
  optionText: { color: Colors.text, fontSize: FontSize.md, flex: 1 },
  optionLoader: { marginLeft: Spacing.sm },
  feedback: {
    marginTop: Spacing.lg,
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  feedbackCorrect: { backgroundColor: "rgba(0,184,148,0.15)" },
  feedbackWrong: { backgroundColor: "rgba(255,107,107,0.15)" },
  feedbackTitle: {
    color: Colors.text,
    fontSize: FontSize.md,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  feedbackText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    lineHeight: 20,
  },
  feedbackAnswer: {
    color: Colors.success,
    fontSize: FontSize.sm,
    fontWeight: "600",
    marginTop: Spacing.xs,
  },
});
