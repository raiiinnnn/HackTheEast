import apiClient from "./client";
import { TokenResponse, UserResponse } from "./types";

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

export async function getMe(): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>("/auth/me");
  return data;
}
