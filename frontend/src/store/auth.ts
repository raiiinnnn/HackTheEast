import { create } from "zustand";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  abelianAddress: string | null;
  setToken: (token: string) => void;
  setAbelianAddress: (address: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  abelianAddress: null,
  setToken: (token: string) => set({ token, isAuthenticated: true }),
  setAbelianAddress: (address: string) => set({ abelianAddress: address }),
  logout: () =>
    set({ token: null, isAuthenticated: false, abelianAddress: null }),
}));
