import axios from "axios";
import { API_BASE_URL, API_PREFIX } from "../constants/api";
import { useAuthStore } from "../store/auth";

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

export default apiClient;
