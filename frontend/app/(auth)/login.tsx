import { useState, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  Pressable,
  ViewStyle,
} from "react-native";
import { Link, router } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import * as Haptics from "expo-haptics";
import { Ionicons } from "@expo/vector-icons";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  FadeInDown,
  FadeIn,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Colors, Spacing, FontSize, BorderRadius } from "../../src/constants/theme";
import { login } from "../../src/api/auth";
import { useAuthStore } from "../../src/store/auth";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

const SPRING_CONFIG = { damping: 18, stiffness: 180 };

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailFocused, setEmailFocused] = useState(false);
  const [passwordFocused, setPasswordFocused] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);
  const insets = useSafeAreaInsets();
  const buttonScale = useSharedValue(1);

  const handleLogin = useCallback(async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please fill in all fields");
      return;
    }
    if (Platform.OS === "ios") {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    setLoading(true);
    try {
      const res = await login(email.trim(), password);
      setToken(res.access_token);
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert("Login failed", e.response?.data?.detail || "Please try again");
    } finally {
      setLoading(false);
    }
  }, [email, password, setToken]);

  const buttonAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: buttonScale.value }],
  }));

  const onPressIn = useCallback(() => {
    buttonScale.value = withSpring(0.97, SPRING_CONFIG);
  }, [buttonScale]);

  const onPressOut = useCallback(() => {
    buttonScale.value = withSpring(1, SPRING_CONFIG);
  }, [buttonScale]);

  const inputBase: ViewStyle = {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderWidth: 1.5,
    gap: 12,
  };

  return (
    <LinearGradient
      colors={["#1a0a2e", "#16213e", "#0f0f23"]}
      locations={[0, 0.5, 1]}
      style={[styles.gradient, { paddingTop: insets.top, paddingBottom: insets.bottom }]}
    >
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 20}
      >
        {/* Header with frosted gear */}
        <Animated.View
          entering={FadeIn.duration(400)}
          style={[styles.header, { paddingTop: insets.top + 8 }]}
        >
          <View style={styles.frostedIconWrap}>
            {Platform.OS === "ios" ? (
              <BlurView intensity={60} tint="dark" style={styles.frostedCircle}>
                <Ionicons name="settings-outline" size={22} color="rgba(255,255,255,0.9)" />
              </BlurView>
            ) : (
              <View style={[styles.frostedCircle, styles.frostedCircleFallback]}>
                <Ionicons name="settings-outline" size={22} color="rgba(255,255,255,0.9)" />
              </View>
            )}
          </View>
        </Animated.View>

        <Animated.View
          entering={FadeInDown.duration(500).springify().damping(18)}
          style={styles.content}
        >
          <Text style={styles.title}>Welcome back</Text>
          <Text style={styles.subtitle}>Sign in to continue to FocusFeed</Text>

          {/* Floating card with blur */}
          <View style={styles.cardWrap}>
            {Platform.OS === "ios" ? (
              <BlurView intensity={50} tint="dark" style={styles.card}>
                <View style={styles.cardInner}>
                  <View
                    style={[
                      inputBase,
                      emailFocused && styles.inputFocused,
                    ]}
                  >
                    <Ionicons
                      name="mail-outline"
                      size={20}
                      color={emailFocused ? Colors.primaryLight : Colors.textMuted}
                    />
                    <TextInput
                      style={styles.inputField}
                      placeholder="Email"
                      placeholderTextColor={Colors.textMuted}
                      value={email}
                      onChangeText={setEmail}
                      onFocus={() => setEmailFocused(true)}
                      onBlur={() => setEmailFocused(false)}
                      autoCapitalize="none"
                      keyboardType="email-address"
                      autoCorrect={false}
                    />
                  </View>
                  <View
                    style={[
                      inputBase,
                      styles.inputSpacer,
                      passwordFocused && styles.inputFocused,
                    ]}
                  >
                    <Ionicons
                      name="lock-closed-outline"
                      size={20}
                      color={passwordFocused ? Colors.primaryLight : Colors.textMuted}
                    />
                    <TextInput
                      style={styles.inputField}
                      placeholder="Password"
                      placeholderTextColor={Colors.textMuted}
                      value={password}
                      onChangeText={setPassword}
                      onFocus={() => setPasswordFocused(true)}
                      onBlur={() => setPasswordFocused(false)}
                      secureTextEntry
                    />
                  </View>

                  <AnimatedPressable
                    onPress={handleLogin}
                    onPressIn={onPressIn}
                    onPressOut={onPressOut}
                    disabled={loading}
                    style={[styles.buttonWrap, buttonAnimatedStyle]}
                  >
                    <LinearGradient
                      colors={[Colors.primary, "#5b4bc9"]}
                      start={{ x: 0, y: 0 }}
                      end={{ x: 1, y: 1 }}
                      style={[styles.button, loading && styles.buttonDisabled]}
                    >
                      {loading ? (
                        <ActivityIndicator color="#fff" size="small" />
                      ) : (
                        <Text style={styles.buttonText}>Sign In</Text>
                      )}
                    </LinearGradient>
                  </AnimatedPressable>

                  <Link href="/(auth)/register" asChild>
                    <Pressable style={styles.linkButton}>
                      <Text style={styles.linkText}>
                        Don't have an account?{" "}
                        <Text style={styles.linkAccent}>Sign Up</Text>
                      </Text>
                    </Pressable>
                  </Link>
                </View>
              </BlurView>
            ) : (
              <View style={[styles.card, styles.cardFallback]}>
                <View style={styles.cardInner}>
                  <View style={[inputBase, emailFocused && styles.inputFocused]}>
                    <Ionicons
                      name="mail-outline"
                      size={20}
                      color={emailFocused ? Colors.primaryLight : Colors.textMuted}
                    />
                    <TextInput
                      style={styles.inputField}
                      placeholder="Email"
                      placeholderTextColor={Colors.textMuted}
                      value={email}
                      onChangeText={setEmail}
                      onFocus={() => setEmailFocused(true)}
                      onBlur={() => setEmailFocused(false)}
                      autoCapitalize="none"
                      keyboardType="email-address"
                      autoCorrect={false}
                    />
                  </View>
                  <View
                    style={[
                      inputBase,
                      styles.inputSpacer,
                      passwordFocused && styles.inputFocused,
                    ]}
                  >
                    <Ionicons
                      name="lock-closed-outline"
                      size={20}
                      color={passwordFocused ? Colors.primaryLight : Colors.textMuted}
                    />
                    <TextInput
                      style={styles.inputField}
                      placeholder="Password"
                      placeholderTextColor={Colors.textMuted}
                      value={password}
                      onChangeText={setPassword}
                      onFocus={() => setPasswordFocused(true)}
                      onBlur={() => setPasswordFocused(false)}
                      secureTextEntry
                    />
                  </View>
                  <AnimatedPressable
                    onPress={handleLogin}
                    onPressIn={onPressIn}
                    onPressOut={onPressOut}
                    disabled={loading}
                    style={[styles.buttonWrap, buttonAnimatedStyle]}
                  >
                    <LinearGradient
                      colors={[Colors.primary, "#5b4bc9"]}
                      start={{ x: 0, y: 0 }}
                      end={{ x: 1, y: 1 }}
                      style={[styles.button, loading && styles.buttonDisabled]}
                    >
                      {loading ? (
                        <ActivityIndicator color="#fff" size="small" />
                      ) : (
                        <Text style={styles.buttonText}>Sign In</Text>
                      )}
                    </LinearGradient>
                  </AnimatedPressable>
                  <Link href="/(auth)/register" asChild>
                    <Pressable style={styles.linkButton}>
                      <Text style={styles.linkText}>
                        Don't have an account?{" "}
                        <Text style={styles.linkAccent}>Sign Up</Text>
                      </Text>
                    </Pressable>
                  </Link>
                </View>
              </View>
            )}
          </View>
        </Animated.View>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    paddingHorizontal: Spacing.xl,
    paddingRight: Spacing.md,
    paddingBottom: 8,
  },
  frostedIconWrap: {
    overflow: "hidden",
    borderRadius: 22,
  },
  frostedCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  frostedCircleFallback: {
    backgroundColor: "rgba(255,255,255,0.12)",
  },
  content: {
    flex: 1,
    paddingHorizontal: Spacing.xl,
    paddingTop: 32,
  },
  title: {
    fontSize: 32,
    fontWeight: "700",
    color: Colors.text,
    letterSpacing: -0.5,
    marginBottom: 8,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 17,
    fontWeight: "400",
    color: Colors.textSecondary,
    marginBottom: 40,
    textAlign: "center",
  },
  cardWrap: {
    marginTop: 8,
  },
  card: {
    borderRadius: 24,
    overflow: "hidden",
    backgroundColor: "rgba(30,30,50,0.4)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.35,
        shadowRadius: 24,
      },
      android: {
        elevation: 12,
      },
    }),
  },
  cardFallback: {
    backgroundColor: "rgba(22,22,42,0.92)",
  },
  cardInner: {
    padding: 24,
  },
  inputFocused: {
    borderColor: "rgba(108,92,231,0.5)",
    backgroundColor: "rgba(255,255,255,0.08)",
  },
  inputSpacer: {
    marginTop: 14,
  },
  inputField: {
    flex: 1,
    fontSize: 16,
    fontWeight: "400",
    color: Colors.text,
    paddingVertical: 0,
  },
  buttonWrap: {
    marginTop: 28,
    borderRadius: 16,
    overflow: "hidden",
  },
  button: {
    paddingVertical: 18,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 16,
    minHeight: 56,
    ...Platform.select({
      ios: {
        shadowColor: Colors.primary,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 12,
      },
      android: {
        elevation: 6,
      },
    }),
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  buttonText: {
    fontSize: 17,
    fontWeight: "600",
    color: "#fff",
  },
  linkButton: {
    alignItems: "center",
    marginTop: 24,
    paddingVertical: 8,
  },
  linkText: {
    fontSize: 15,
    color: Colors.textSecondary,
    fontWeight: "400",
  },
  linkAccent: {
    color: Colors.primaryLight,
    fontWeight: "600",
  },
});
