import apiClient from "./client";
import {
  TokenResponse,
  UserResponse,
  AbelianKeypair,
  AbelianChallengeResponse,
} from "./types";

// --- Email + Password ---

export async function register(
  email: string,
  password: string,
  displayName?: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/register", {
    email,
    password,
    display_name: displayName,
  });
  return data;
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", {
    email,
    password,
  });
  return data;
}

// --- Google OAuth ---

export async function loginGoogle(idToken: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/google", {
    id_token: idToken,
  });
  return data;
}

// --- Abelian Wallet ---

export async function abelianGenerate(): Promise<AbelianKeypair> {
  const { data } = await apiClient.post<AbelianKeypair>(
    "/auth/abelian/generate"
  );
  return data;
}

export async function abelianRegister(
  cryptoAddress: string,
  displayName?: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>(
    "/auth/abelian/register",
    {
      crypto_address: cryptoAddress,
      display_name: displayName,
    }
  );
  return data;
}

export async function abelianChallenge(
  cryptoAddress: string
): Promise<AbelianChallengeResponse> {
  const { data } = await apiClient.post<AbelianChallengeResponse>(
    "/auth/abelian/challenge",
    {
      crypto_address: cryptoAddress,
    }
  );
  return data;
}

export async function abelianVerify(
  cryptoAddress: string,
  challenge: string,
  signature: string
): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>(
    "/auth/abelian/verify",
    {
      crypto_address: cryptoAddress,
      challenge,
      signature,
    }
  );
  return data;
}

// --- Current User ---

export async function getMe(): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>("/auth/me");
  return data;
}

export async function updatePreferences(prefs: {
  video_duration_pref?: string;
  reel_types_pref?: string[];
}): Promise<UserResponse> {
  const { data } = await apiClient.put<UserResponse>(
    "/auth/preferences",
    prefs
  );
  return data;
}
