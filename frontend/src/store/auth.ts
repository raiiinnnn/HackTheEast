import { create } from "zustand";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  setToken: (token: string) => set({ token, isAuthenticated: true }),
  logout: () => set({ token: null, isAuthenticated: false }),
}));
