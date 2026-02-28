import { Platform } from "react-native";

const DEV_BACKEND =
  Platform.OS === "android" ? "http://10.0.2.2:8000" : "http://localhost:8000";

export const API_BASE_URL = DEV_BACKEND;
export const API_PREFIX = "/api/v1";

export const GOOGLE_CLIENT_ID = "751338818813-icshqis3bqu3tb92b3bk0tu3eoq3mipp.apps.googleusercontent.com";
export const GOOGLE_IOS_CLIENT_ID = "751338818813-6bsmp1nmhktifegt2eko07erdg7lgsn5.apps.googleusercontent.com";

