import { Platform } from "react-native";

// On iOS Simulator, "localhost" is the simulator, not your Mac. Set EXPO_PUBLIC_API_BASE_URL
// in .env to your Mac's IP (e.g. http://10.89.14.163:8000) so the app can reach the backend.
const DEFAULT_IOS = "http://localhost:8000";
const DEFAULT_ANDROID = "http://10.0.2.2:8000";

const DEV_BACKEND =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  (Platform.OS === "android" ? DEFAULT_ANDROID : DEFAULT_IOS);

export const API_BASE_URL = DEV_BACKEND;
export const API_PREFIX = "/api/v1";

export const GOOGLE_CLIENT_ID = "751338818813-icshqis3bqu3tb92b3bk0tu3eoq3mipp.apps.googleusercontent.com";
export const GOOGLE_IOS_CLIENT_ID = "751338818813-6bsmp1nmhktifegt2eko07erdg7lgsn5.apps.googleusercontent.com";

