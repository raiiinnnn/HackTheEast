import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from "react-native";
import { Link, router } from "expo-router";
import { Colors, Spacing, FontSize, BorderRadius } from "../../src/constants/theme";
import { register } from "../../src/api/auth";
import { useAuthStore } from "../../src/store/auth";

export default function RegisterScreen() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);

  const handleRegister = async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const res = await register(email.trim(), password, name.trim() || undefined);
      setToken(res.access_token);
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert("Registration failed", e.response?.data?.detail || "Please try again");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <Text style={styles.logo}>FocusFeed</Text>
        <Text style={styles.subtitle}>Create your account</Text>

        <View style={styles.form}>
          <TextInput
            style={styles.input}
            placeholder="Display Name"
            placeholderTextColor={Colors.textMuted}
            value={name}
            onChangeText={setName}
          />
          <TextInput
            style={styles.input}
            placeholder="Email"
            placeholderTextColor={Colors.textMuted}
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
          />
          <TextInput
            style={styles.input}
            placeholder="Password"
            placeholderTextColor={Colors.textMuted}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          <Link href="/(auth)/login" asChild>
            <TouchableOpacity style={styles.linkButton}>
              <Text style={styles.linkText}>
                Already have an account? <Text style={styles.linkBold}>Sign In</Text>
              </Text>
            </TouchableOpacity>
          </Link>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  inner: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: Spacing.xl,
  },
  logo: {
    fontSize: FontSize.hero,
    fontWeight: "800",
    color: Colors.primary,
    textAlign: "center",
    marginBottom: Spacing.xs,
  },
  subtitle: {
    fontSize: FontSize.md,
    color: Colors.textSecondary,
    textAlign: "center",
    marginBottom: Spacing.xxl,
  },
  form: {
    gap: Spacing.md,
  },
  input: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: FontSize.md,
    color: Colors.text,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  button: {
    backgroundColor: Colors.primary,
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.md,
    alignItems: "center",
    marginTop: Spacing.sm,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: Colors.text,
    fontSize: FontSize.lg,
    fontWeight: "700",
  },
  linkButton: {
    alignItems: "center",
    marginTop: Spacing.md,
  },
  linkText: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
  },
  linkBold: {
    color: Colors.primary,
    fontWeight: "700",
  },
});
