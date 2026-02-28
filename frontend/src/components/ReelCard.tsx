import { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from "react-native";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";
import { ReelResponse } from "../api/types";

interface Props {
  reel: ReelResponse;
  isActive: boolean;
  onWatched: () => void;
}

export default function ReelCard({ reel, isActive, onWatched }: Props) {
  const [liked, setLiked] = useState(false);
  const [saved, setSaved] = useState(false);
  const [hasTracked, setHasTracked] = useState(false);

  useEffect(() => {
    if (isActive && !hasTracked) {
      const timer = setTimeout(() => {
        onWatched();
        setHasTracked(true);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isActive, hasTracked]);

  return (
    <View style={styles.container}>
      <View style={styles.visualArea}>
        <View style={styles.gradientOverlay}>
          <Text style={styles.durationBadge}>{reel.duration_seconds}s</Text>
        </View>
        <View style={styles.visualContent}>
          <Text style={styles.playIcon}>▶</Text>
          <Text style={styles.visualLabel}>Reel</Text>
        </View>
      </View>

      <View style={styles.infoSection}>
        <Text style={styles.title} numberOfLines={2}>
          {reel.title}
        </Text>

        <ScrollView
          style={styles.scriptScroll}
          showsVerticalScrollIndicator={false}
          nestedScrollEnabled
        >
          <Text style={styles.script}>{reel.script}</Text>
        </ScrollView>

        {reel.captions && reel.captions !== reel.script && (
          <Text style={styles.captions} numberOfLines={2}>
            {reel.captions}
          </Text>
        )}
      </View>

      <View style={styles.actions}>
        <TouchableOpacity
          style={styles.actionBtn}
          onPress={() => setLiked(!liked)}
        >
          <Text style={styles.actionIcon}>{liked ? "❤️" : "🤍"}</Text>
          <Text style={styles.actionLabel}>Like</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.actionBtn}
          onPress={() => setSaved(!saved)}
        >
          <Text style={styles.actionIcon}>{saved ? "🔖" : "📑"}</Text>
          <Text style={styles.actionLabel}>Save</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.actionBtn}>
          <Text style={styles.actionIcon}>📤</Text>
          <Text style={styles.actionLabel}>Share</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.card,
    borderRadius: BorderRadius.xl,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  visualArea: {
    height: "35%",
    backgroundColor: Colors.surface,
    justifyContent: "center",
    alignItems: "center",
    position: "relative",
  },
  gradientOverlay: {
    position: "absolute",
    top: Spacing.sm,
    right: Spacing.sm,
    zIndex: 1,
  },
  durationBadge: {
    backgroundColor: "rgba(0,0,0,0.6)",
    color: "#fff",
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.sm,
    fontSize: FontSize.xs,
    fontWeight: "600",
  },
  visualContent: { alignItems: "center" },
  playIcon: {
    fontSize: 48,
    color: Colors.primary,
    marginBottom: Spacing.xs,
  },
  visualLabel: { color: Colors.textMuted, fontSize: FontSize.sm },
  infoSection: {
    flex: 1,
    padding: Spacing.md,
  },
  title: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
    marginBottom: Spacing.sm,
  },
  scriptScroll: { flex: 1 },
  script: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    lineHeight: 22,
  },
  captions: {
    color: Colors.textMuted,
    fontSize: FontSize.sm,
    fontStyle: "italic",
    marginTop: Spacing.sm,
  },
  actions: {
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  actionBtn: { alignItems: "center" },
  actionIcon: { fontSize: 22, marginBottom: 2 },
  actionLabel: { color: Colors.textMuted, fontSize: FontSize.xs },
});
