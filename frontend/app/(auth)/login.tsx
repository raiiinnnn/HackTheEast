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
import * as Google from "expo-auth-session/providers/google";
import * as WebBrowser from "expo-web-browser";
import * as SecureStore from "expo-secure-store";
import {
  Colors,
  Spacing,
  FontSize,
  BorderRadius,
} from "../../src/constants/theme";
import { GOOGLE_CLIENT_ID } from "../../src/constants/api";
import {
  login,
  loginGoogle,
  abelianChallenge,
  abelianVerify,
} from "../../src/api/auth";
import { useAuthStore } from "../../src/store/auth";

WebBrowser.maybeCompleteAuthSession();

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [abelianLoading, setAbelianLoading] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);
  const setAbelianAddress = useAuthStore((s) => s.setAbelianAddress);

  const [_request, response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: GOOGLE_CLIENT_ID,
  });

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const res = await login(email.trim(), password);
      setToken(res.access_token);
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert(
        "Login failed",
        e.response?.data?.detail || "Please try again"
      );
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setGoogleLoading(true);
    try {
      const result = await promptAsync();
      if (result?.type === "success" && result.params?.id_token) {
        const res = await loginGoogle(result.params.id_token);
        setToken(res.access_token);
        router.replace("/(tabs)");
      }
    } catch (e: any) {
      Alert.alert(
        "Google sign-in failed",
        e.response?.data?.detail || "Please try again"
      );
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleAbelian = async () => {
    setAbelianLoading(true);
    try {
      const stored = await SecureStore.getItemAsync("abelian_address");
      const storedSk = await SecureStore.getItemAsync("abelian_sk");

      if (!stored || !storedSk) {
        Alert.alert(
          "No Wallet Found",
          "You need to create an Abelian wallet first. Go to Sign Up."
        );
        setAbelianLoading(false);
        return;
      }

      const challengeRes = await abelianChallenge(stored);

      const signResp = await fetch("http://localhost:8001/sign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: challengeRes.challenge,
          spend_secret_key: storedSk,
        }),
      });
      const signData = await signResp.json();

      const res = await abelianVerify(
        stored,
        challengeRes.challenge,
        signData.signature
      );
      setAbelianAddress(stored);
      setToken(res.access_token);
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert(
        "Abelian sign-in failed",
        e.response?.data?.detail || e.message || "Please try again"
      );
    } finally {
      setAbelianLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.inner}>
        <Text style={styles.logo}>FocusFeed</Text>
        <Text style={styles.subtitle}>Learn smarter, one reel at a time</Text>

        <View style={styles.form}>
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
            onPress={handleLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Sign In</Text>
            )}
          </TouchableOpacity>

          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          <TouchableOpacity
            style={[styles.socialButton, styles.googleButton, googleLoading && styles.buttonDisabled]}
            onPress={handleGoogle}
            disabled={googleLoading}
          >
            {googleLoading ? (
              <ActivityIndicator color="#000" />
            ) : (
              <>
                <Text style={styles.socialIcon}>G</Text>
                <Text style={styles.googleButtonText}>
                  Continue with Google
                </Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.socialButton, styles.abelianButton, abelianLoading && styles.buttonDisabled]}
            onPress={handleAbelian}
            disabled={abelianLoading}
          >
            {abelianLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Text style={styles.socialIcon}>Q</Text>
                <Text style={styles.abelianButtonText}>
                  Sign in with Abelian
                </Text>
              </>
            )}
          </TouchableOpacity>

          <Link href="/(auth)/register" asChild>
            <TouchableOpacity style={styles.linkButton}>
              <Text style={styles.linkText}>
                Don't have an account?{" "}
                <Text style={styles.linkBold}>Sign Up</Text>
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
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: Spacing.sm,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: Colors.border,
  },
  dividerText: {
    color: Colors.textMuted,
    paddingHorizontal: Spacing.md,
    fontSize: FontSize.sm,
  },
  socialButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.md,
    gap: Spacing.sm,
  },
  googleButton: {
    backgroundColor: "#FFFFFF",
  },
  googleButtonText: {
    color: "#000000",
    fontSize: FontSize.md,
    fontWeight: "600",
  },
  abelianButton: {
    backgroundColor: Colors.surfaceLight,
    borderWidth: 1,
    borderColor: Colors.secondary,
  },
  abelianButtonText: {
    color: Colors.secondary,
    fontSize: FontSize.md,
    fontWeight: "600",
  },
  socialIcon: {
    fontSize: FontSize.lg,
    fontWeight: "800",
    width: 24,
    textAlign: "center",
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
