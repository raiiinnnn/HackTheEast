import { useState, useEffect } from "react";
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Platform,
} from "react-native";
import { Colors, Spacing, FontSize, BorderRadius } from "../constants/theme";

interface MnemonicDisplayProps {
  visible: boolean;
  words: string[];
  onConfirm: () => void;
}

export function MnemonicDisplayModal({
  visible,
  words,
  onConfirm,
}: MnemonicDisplayProps) {
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (visible) setConfirmed(false);
  }, [visible]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      statusBarTranslucent
    >
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <ScrollView showsVerticalScrollIndicator={false}>
            <Text style={styles.title}>Your Recovery Phrase</Text>
            <Text style={styles.subtitle}>
              Write down these 24 words in order. This is the only way to
              recover your quantum wallet on another device.
            </Text>

            <View style={styles.grid}>
              {words.map((word, i) => (
                <View key={i} style={styles.wordCell}>
                  <Text style={styles.wordIndex}>{i + 1}</Text>
                  <Text style={styles.wordText}>{word}</Text>
                </View>
              ))}
            </View>

            <TouchableOpacity
              style={styles.checkboxRow}
              onPress={() => setConfirmed((c) => !c)}
              activeOpacity={0.7}
            >
              <View
                style={[styles.checkbox, confirmed && styles.checkboxChecked]}
              >
                {confirmed && <Text style={styles.checkmark}>✓</Text>}
              </View>
              <Text style={styles.checkboxLabel}>
                I have written down my recovery phrase
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.button, !confirmed && styles.buttonDisabled]}
              onPress={onConfirm}
              disabled={!confirmed}
            >
              <Text style={styles.buttonText}>Continue</Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

interface MnemonicInputProps {
  visible: boolean;
  onSubmit: (mnemonic: string) => void;
  onCancel: () => void;
  loading?: boolean;
}

export function MnemonicInputModal({
  visible,
  onSubmit,
  onCancel,
  loading,
}: MnemonicInputProps) {
  const [phrase, setPhrase] = useState("");

  useEffect(() => {
    if (visible) setPhrase("");
  }, [visible]);

  const wordCount = phrase.trim().split(/\s+/).filter(Boolean).length;
  const isValid = wordCount === 24;

  const handleSubmit = () => {
    if (!isValid) return;
    onSubmit(phrase.trim().toLowerCase());
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      statusBarTranslucent
    >
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <ScrollView
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
          >
            <Text style={styles.title}>Restore Wallet</Text>
            <Text style={styles.subtitle}>
              Enter your 24-word recovery phrase to restore your quantum wallet
              on this device.
            </Text>

            <TextInput
              style={styles.phraseInput}
              value={phrase}
              onChangeText={setPhrase}
              placeholder="word1 word2 word3 ... word24"
              placeholderTextColor={Colors.textMuted}
              multiline
              autoCapitalize="none"
              autoCorrect={false}
              textAlignVertical="top"
            />

            <Text
              style={[styles.wordCount, isValid ? styles.valid : styles.invalid]}
            >
              {wordCount} / 24 words
            </Text>

            <TouchableOpacity
              style={[
                styles.button,
                (!isValid || loading) && styles.buttonDisabled,
              ]}
              onPress={handleSubmit}
              disabled={!isValid || loading}
            >
              <Text style={styles.buttonText}>
                {loading ? "Restoring..." : "Restore Wallet"}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.cancelButton}
              onPress={onCancel}
              disabled={loading}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.7)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: Colors.surface,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    padding: Spacing.xl,
    paddingBottom: Platform.OS === "ios" ? 48 : Spacing.xl,
    maxHeight: "90%",
  },
  title: {
    fontSize: FontSize.xl,
    fontWeight: "800",
    color: Colors.secondary,
    textAlign: "center",
    marginBottom: Spacing.sm,
  },
  subtitle: {
    fontSize: FontSize.sm,
    color: Colors.textSecondary,
    textAlign: "center",
    marginBottom: Spacing.lg,
    lineHeight: 20,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginBottom: Spacing.lg,
  },
  wordCell: {
    width: "30%",
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.sm,
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.sm,
    marginBottom: Spacing.sm,
  },
  wordIndex: {
    fontSize: FontSize.xs,
    color: Colors.textMuted,
    width: 20,
    textAlign: "right",
    marginRight: Spacing.xs,
  },
  wordText: {
    fontSize: FontSize.sm,
    color: Colors.text,
    fontWeight: "600",
    flex: 1,
  },
  checkboxRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: Spacing.lg,
    gap: Spacing.sm,
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 4,
    borderWidth: 2,
    borderColor: Colors.textMuted,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxChecked: {
    borderColor: Colors.secondary,
    backgroundColor: Colors.secondary,
  },
  checkmark: {
    color: Colors.background,
    fontSize: 14,
    fontWeight: "800",
  },
  checkboxLabel: {
    color: Colors.textSecondary,
    fontSize: FontSize.sm,
    flex: 1,
  },
  button: {
    backgroundColor: Colors.secondary,
    borderRadius: BorderRadius.md,
    paddingVertical: Spacing.md,
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  buttonText: {
    color: Colors.background,
    fontSize: FontSize.md,
    fontWeight: "700",
  },
  phraseInput: {
    backgroundColor: Colors.surfaceLight,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: FontSize.md,
    color: Colors.text,
    minHeight: 120,
    marginBottom: Spacing.sm,
  },
  wordCount: {
    fontSize: FontSize.xs,
    textAlign: "right",
    marginBottom: Spacing.lg,
  },
  valid: {
    color: Colors.success,
  },
  invalid: {
    color: Colors.textMuted,
  },
  cancelButton: {
    alignItems: "center",
    marginTop: Spacing.md,
  },
  cancelText: {
    color: Colors.textMuted,
    fontSize: FontSize.md,
  },
});
