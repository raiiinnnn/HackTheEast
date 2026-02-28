import { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Platform,
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

export default function ProfileScreen() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleDurationChange = async (pref: string) => {
    if (!user || pref === user.video_duration_pref) return;
    setSaving(true);
    try {
      const updated = await updatePreferences(pref);
      setUser(updated);
    } catch {
      const msg = "Failed to save preference";
      Platform.OS === "web" ? window.alert(msg) : null;
    } finally {
      setSaving(false);
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

  return (
    <View style={styles.container}>
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
                disabled={saving}
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
        {saving && (
          <ActivityIndicator
            color={Colors.primary}
            size="small"
            style={{ marginTop: Spacing.sm }}
          />
        )}
      </View>

      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    alignItems: "center",
    paddingTop: 60,
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

  // Preference section
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
  optionLabelActive: {
    color: Colors.primary,
  },
  optionDetail: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    marginTop: 2,
  },
  optionDetailActive: {
    color: Colors.primaryLight,
  },
  activeDot: {
    position: "absolute",
    top: 8,
    right: 8,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.primary,
  },

  logoutBtn: {
    backgroundColor: Colors.error,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  logoutText: { color: "#fff", fontSize: FontSize.md, fontWeight: "600" },
});
