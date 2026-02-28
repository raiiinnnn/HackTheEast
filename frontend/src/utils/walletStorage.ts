import { Platform } from "react-native";

const KEYS = {
  address: "abelian_address",
  sk: "abelian_sk",
  mnemonic: "abelian_mnemonic",
} as const;

export interface WalletData {
  address: string;
  sk: string;
  mnemonic: string;
}

async function nativeSet(key: string, value: string): Promise<void> {
  const SecureStore = await import("expo-secure-store");
  await SecureStore.setItemAsync(key, value);
}

async function nativeGet(key: string): Promise<string | null> {
  const SecureStore = await import("expo-secure-store");
  return SecureStore.getItemAsync(key);
}

async function nativeDelete(key: string): Promise<void> {
  const SecureStore = await import("expo-secure-store");
  await SecureStore.deleteItemAsync(key);
}

function webSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    console.warn("localStorage unavailable");
  }
}

function webGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function webDelete(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {
    // noop
  }
}

const isWeb = Platform.OS === "web";

export async function saveWallet(
  address: string,
  sk: string,
  mnemonic: string
): Promise<void> {
  if (isWeb) {
    webSet(KEYS.address, address);
    webSet(KEYS.sk, sk);
    webSet(KEYS.mnemonic, mnemonic);
  } else {
    await nativeSet(KEYS.address, address);
    await nativeSet(KEYS.sk, sk);
    await nativeSet(KEYS.mnemonic, mnemonic);
  }
}

export async function loadWallet(): Promise<WalletData | null> {
  let address: string | null;
  let sk: string | null;
  let mnemonic: string | null;

  if (isWeb) {
    address = webGet(KEYS.address);
    sk = webGet(KEYS.sk);
    mnemonic = webGet(KEYS.mnemonic);
  } else {
    address = await nativeGet(KEYS.address);
    sk = await nativeGet(KEYS.sk);
    mnemonic = await nativeGet(KEYS.mnemonic);
  }

  if (!address || !sk) return null;
  return { address, sk, mnemonic: mnemonic ?? "" };
}

export async function clearWallet(): Promise<void> {
  if (isWeb) {
    webDelete(KEYS.address);
    webDelete(KEYS.sk);
    webDelete(KEYS.mnemonic);
  } else {
    await nativeDelete(KEYS.address);
    await nativeDelete(KEYS.sk);
    await nativeDelete(KEYS.mnemonic);
  }
}
