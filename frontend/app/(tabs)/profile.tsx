import { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Platform,
  ScrollView,
} from "react-native";
import { router } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../../src/constants/theme";
import { getMe, updatePreferences } from "../../src/api/auth";
import { useAuthStore } from "../../src/store/auth";
import { UserResponse } from "../../src/api/types";

const DURATION_OPTIONS = [
  { key: "short", label: "Short", detail: "20–35s" },
  { key: "medium", label: "Medium", detail: "35–50s" },
  { key: "long", label: "Long", detail: "50s+" },
] as const;

const REEL_TYPE_OPTIONS = [
  {
    key: "clips",
    label: "Video Clips",
    detail: "Clippings of lectures & open-source teaching materials",
    icon: "🎬",
  },
  {
    key: "slides_voiceover",
    label: "Slides + Voiceover",
    detail: "Slides with professor voiceovers",
    icon: "🎙️",
  },
  {
    key: "ai_character",
    label: "AI Character",
    detail: "AI character explanations",
    icon: "🤖",
  },
] as const;

export default function ProfileScreen() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingDuration, setSavingDuration] = useState(false);
  const [savingTypes, setSavingTypes] = useState(false);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleDurationChange = async (pref: string) => {
    if (!user || pref === user.video_duration_pref) return;
    setSavingDuration(true);
    try {
      const updated = await updatePreferences({ video_duration_pref: pref });
      setUser(updated);
    } catch {
      if (Platform.OS === "web") window.alert("Failed to save preference");
    } finally {
      setSavingDuration(false);
    }
  };

  const handleReelTypeToggle = async (key: string) => {
    if (!user) return;
    const current = user.reel_types_pref || ["clips"];
    let next: string[];
    if (current.includes(key)) {
      next = current.filter((k) => k !== key);
      if (next.length === 0) {
        if (Platform.OS === "web") window.alert("Select at least one reel type");
        return;
      }
    } else {
      next = [...current, key];
    }
    setSavingTypes(true);
    try {
      const updated = await updatePreferences({ reel_types_pref: next });
      setUser(updated);
    } catch {
      if (Platform.OS === "web") window.alert("Failed to save preference");
    } finally {
      setSavingTypes(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.replace("/(auth)/login");
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  const reelTypes = user?.reel_types_pref || ["clips"];

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.container}
    >
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>
          {user?.display_name?.[0]?.toUpperCase() ||
            user?.email?.[0]?.toUpperCase() ||
            "?"}
        </Text>
      </View>
      <Text style={styles.name}>{user?.display_name || "Student"}</Text>
      <Text style={styles.email}>{user?.email}</Text>

      {/* Video Duration Preference */}
      <View style={styles.prefSection}>
        <Text style={styles.prefTitle}>Preferred Reel Length</Text>
        <Text style={styles.prefDesc}>
          Choose the video duration that works best for you
        </Text>
        <View style={styles.optionsRow}>
          {DURATION_OPTIONS.map((opt) => {
            const isActive = user?.video_duration_pref === opt.key;
            return (
              <TouchableOpacity
                key={opt.key}
                style={[styles.optionCard, isActive && styles.optionCardActive]}
                onPress={() => handleDurationChange(opt.key)}
                disabled={savingDuration}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.optionLabel,
                    isActive && styles.optionLabelActive,
                  ]}
                >
                  {opt.label}
                </Text>
                <Text
                  style={[
                    styles.optionDetail,
                    isActive && styles.optionDetailActive,
                  ]}
                >
                  {opt.detail}
                </Text>
                {isActive && <View style={styles.activeDot} />}
              </TouchableOpacity>
            );
          })}
        </View>
        {savingDuration && (
          <ActivityIndicator
            color={Colors.primary}
            size="small"
            style={{ marginTop: Spacing.sm }}
          />
        )}
      </View>

      {/* Reel Type Preference */}
      <View style={styles.prefSection}>
        <Text style={styles.prefTitle}>Reel Generation Style</Text>
        <Text style={styles.prefDesc}>
          Pick the types of reels you'd like generated (select multiple)
        </Text>
        <View style={styles.typesList}>
          {REEL_TYPE_OPTIONS.map((opt) => {
            const isActive = reelTypes.includes(opt.key);
            return (
              <TouchableOpacity
                key={opt.key}
                style={[styles.typeCard, isActive && styles.typeCardActive]}
                onPress={() => handleReelTypeToggle(opt.key)}
                disabled={savingTypes}
                activeOpacity={0.7}
              >
                <View style={styles.typeLeft}>
                  <Text style={styles.typeIcon}>{opt.icon}</Text>
                  <View style={styles.typeText}>
                    <Text
                      style={[
                        styles.typeLabel,
                        isActive && styles.typeLabelActive,
                      ]}
                    >
                      {opt.label}
                    </Text>
                    <Text style={styles.typeDetail}>{opt.detail}</Text>
                  </View>
                </View>
                <View
                  style={[
                    styles.checkbox,
                    isActive && styles.checkboxActive,
                  ]}
                >
                  {isActive && <Text style={styles.checkmark}>✓</Text>}
                </View>
              </TouchableOpacity>
            );
          })}
        </View>
        {savingTypes && (
          <ActivityIndicator
            color={Colors.secondary}
            size="small"
            style={{ marginTop: Spacing.sm }}
          />
        )}
      </View>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  container: {
    alignItems: "center",
    paddingTop: 60,
    paddingBottom: 40,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.background,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.primary,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  avatarText: { color: "#fff", fontSize: FontSize.xxl, fontWeight: "700" },
  name: {
    color: Colors.text,
    fontSize: FontSize.xl,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  email: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    marginBottom: Spacing.xl,
  },

  prefSection: {
    width: "100%",
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.xl,
  },
  prefTitle: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
    marginBottom: Spacing.xs,
  },
  prefDesc: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    marginBottom: Spacing.md,
  },

  // Duration row
  optionsRow: {
    flexDirection: "row",
    gap: Spacing.sm,
  },
  optionCard: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    paddingVertical: Spacing.md,
    alignItems: "center",
    borderWidth: 2,
    borderColor: Colors.border,
    position: "relative",
  },
  optionCardActive: {
    borderColor: Colors.primary,
    backgroundColor: "rgba(108,92,231,0.12)",
  },
  optionLabel: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    fontWeight: "700",
  },
  optionLabelActive: { color: Colors.primary },
  optionDetail: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    marginTop: 2,
  },
  optionDetailActive: { color: Colors.primaryLight },
  activeDot: {
    position: "absolute",
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.primary,
  },

  // Reel type list
  typesList: {
    gap: Spacing.sm,
  },
  typeCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    borderWidth: 2,
    borderColor: Colors.border,
  },
  typeCardActive: {
    borderColor: Colors.secondary,
    backgroundColor: "rgba(0,206,201,0.08)",
  },
  typeLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
    gap: Spacing.md,
  },
  typeIcon: { fontSize: 28 },
  typeText: { flex: 1 },
  typeLabel: {
    color: Colors.textSecondary,
    fontSize: FontSize.md,
    fontWeight: "700",
  },
  typeLabelActive: { color: Colors.secondary },
  typeDetail: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    marginTop: 2,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: Colors.border,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: Spacing.sm,
  },
  checkboxActive: {
    borderColor: Colors.secondary,
    backgroundColor: Colors.secondary,
  },
  checkmark: {
    color: "#fff",
    fontSize: 14,
    fontWeight: "800",
  },

  logoutBtn: {
    backgroundColor: Colors.error,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  logoutText: { color: "#fff", fontSize: FontSize.md, fontWeight: "600" },
});
