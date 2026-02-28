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
  ScrollView,
  Modal,
} from "react-native";
import { Link, router } from "expo-router";
import * as Google from "expo-auth-session/providers/google";
import * as WebBrowser from "expo-web-browser";
import {
  Colors,
  Spacing,
  FontSize,
  BorderRadius,
} from "../../src/constants/theme";
import { GOOGLE_CLIENT_ID, GOOGLE_IOS_CLIENT_ID } from "../../src/constants/api";
import {
  register,
  loginGoogle,
  abelianGenerate,
  abelianRegister,
} from "../../src/api/auth";
import { useAuthStore } from "../../src/store/auth";
import { saveWallet, loadWallet } from "../../src/utils/walletStorage";
import { MnemonicDisplayModal } from "../../src/components/MnemonicModal";

WebBrowser.maybeCompleteAuthSession();

export default function RegisterScreen() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [abelianLoading, setAbelianLoading] = useState(false);
  const [mnemonicWords, setMnemonicWords] = useState<string[]>([]);
  const [showMnemonic, setShowMnemonic] = useState(false);
  const [showWalletName, setShowWalletName] = useState(false);
  const [walletName, setWalletName] = useState("");
  const setToken = useAuthStore((s) => s.setToken);
  const setAbelianAddress = useAuthStore((s) => s.setAbelianAddress);

  const [pendingToken, setPendingToken] = useState<string | null>(null);
  const [pendingAddress, setPendingAddress] = useState<string | null>(null);

  const [_request, _response, promptAsync] = Google.useIdTokenAuthRequest({
    clientId: GOOGLE_CLIENT_ID,
    iosClientId: GOOGLE_IOS_CLIENT_ID,
  });

  const handleRegister = async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const res = await register(
        email.trim(),
        password,
        name.trim() || undefined
      );
      setToken(res.access_token);
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert(
        "Registration failed",
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

  const confirmAndCreate = async (displayName: string) => {
    setShowWalletName(false);
    setAbelianLoading(true);
    try {
      const keypair = await abelianGenerate();
      const mnemonic = keypair.mnemonic.join(" ");

      await saveWallet(keypair.crypto_address, keypair.spend_secret_key, mnemonic);

      const res = await abelianRegister(
        keypair.crypto_address,
        displayName || "Abelian User"
      );

      setPendingToken(res.access_token);
      setPendingAddress(keypair.crypto_address);
      setMnemonicWords(keypair.mnemonic);
      setShowMnemonic(true);
    } catch (e: any) {
      Alert.alert(
        "Abelian registration failed",
        e.response?.data?.detail || e.message || "Please try again"
      );
    } finally {
      setAbelianLoading(false);
    }
  };

  const promptWalletName = () => {
    setWalletName("");
    setShowWalletName(true);
  };

  const handleAbelian = async () => {
    const existing = await loadWallet();
    if (existing) {
      Alert.alert(
        "Wallet Exists",
        "A quantum wallet already exists on this device. Creating a new one will replace it and you'll lose access to the old account.",
        [
          { text: "Cancel", style: "cancel" },
          { text: "Replace", style: "destructive", onPress: promptWalletName },
        ]
      );
      return;
    }
    promptWalletName();
  };

  const handleMnemonicConfirm = () => {
    setShowMnemonic(false);
    if (pendingToken && pendingAddress) {
      setAbelianAddress(pendingAddress);
      setToken(pendingToken);
      router.replace("/(tabs)");
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.inner}
        keyboardShouldPersistTaps="handled"
      >
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

          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          <TouchableOpacity
            style={[
              styles.socialButton,
              styles.googleButton,
              googleLoading && styles.buttonDisabled,
            ]}
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
            style={[
              styles.socialButton,
              styles.abelianButton,
              abelianLoading && styles.buttonDisabled,
            ]}
            onPress={handleAbelian}
            disabled={abelianLoading}
          >
            {abelianLoading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <Text style={[styles.socialIcon, { color: Colors.secondary }]}>
                  Q
                </Text>
                <Text style={styles.abelianButtonText}>
                  Create Quantum Wallet
                </Text>
              </>
            )}
          </TouchableOpacity>

          <Text style={styles.abelianInfo}>
            Abelian uses CRYSTALS-Dilithium — a NIST-approved post-quantum
            signature algorithm — for quantum-resistant authentication.
          </Text>

          <Link href="/(auth)/login" asChild>
            <TouchableOpacity style={styles.linkButton}>
              <Text style={styles.linkText}>
                Already have an account?{" "}
                <Text style={styles.linkBold}>Sign In</Text>
              </Text>
            </TouchableOpacity>
          </Link>
        </View>
      </ScrollView>

      <Modal
        visible={showWalletName}
        animationType="slide"
        transparent
        statusBarTranslucent
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <Text style={styles.modalTitle}>Create Quantum Wallet</Text>
            <Text style={styles.modalSubtitle}>
              Choose a display name for your wallet account
            </Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Display Name"
              placeholderTextColor={Colors.textMuted}
              value={walletName}
              onChangeText={setWalletName}
              autoFocus
            />
            <TouchableOpacity
              style={[
                styles.modalButton,
                !walletName.trim() && styles.buttonDisabled,
              ]}
              onPress={() => confirmAndCreate(walletName.trim())}
              disabled={!walletName.trim()}
            >
              <Text style={styles.modalButtonText}>Generate Wallet</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.modalCancel}
              onPress={() => setShowWalletName(false)}
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      <MnemonicDisplayModal
        visible={showMnemonic}
        words={mnemonicWords}
        onConfirm={handleMnemonicConfirm}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  inner: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.xxl,
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
  abelianInfo: {
    color: Colors.textMuted,
    fontSize: FontSize.xs,
    textAlign: "center",
    lineHeight: 18,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "center",
    paddingHorizontal: Spacing.xl,
  },
  modalSheet: {
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.xl,
  },
  modalTitle: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.secondary,
    textAlign: "center",
    marginBottom: Spacing.sm,
  },
  modalSubtitle: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    textAlign: "center",
    marginBottom: Spacing.lg,
  },
  modalInput: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: FontSize.md,
    color: Colors.text,
    marginBottom: Spacing.lg,
  },
  modalButton: {
    backgroundColor: Colors.secondary,
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.md,
    alignItems: "center",
  },
  modalButtonText: {
    color: Colors.background,
    fontSize: FontSize.md,
    fontWeight: "700",
  },
  modalCancel: {
    alignItems: "center",
    marginTop: Spacing.md,
  },
  modalCancelText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
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
