import { Platform } from "react-native";

const DEV_BACKEND =
  Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";

export const API_BASE_URL = DEV_BACKEND;
export const API_PREFIX = "/api/v1";
