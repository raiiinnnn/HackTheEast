import { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { router } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../../src/constants/theme";
import { getMe } from "../../src/api/auth";
import { useAuthStore } from "../../src/store/auth";
import { UserResponse } from "../../src/api/types";

export default function ProfileScreen() {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

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
          {user?.display_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "?"}
        </Text>
      </View>
      <Text style={styles.name}>{user?.display_name || "Student"}</Text>
      <Text style={styles.email}>{user?.email}</Text>

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
  email: { color: Colors.textSecondary, fontSize: FontSize.md, marginBottom: Spacing.xxl },
  logoutBtn: {
    backgroundColor: Colors.error,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  logoutText: { color: "#fff", fontSize: FontSize.md, fontWeight: "600" },
});
