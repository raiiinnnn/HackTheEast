import { Platform } from "react-native";
import apiClient from "./client";
import { UploadedMaterialResponse } from "./types";

export async function uploadMaterial(
  courseId: number,
  fileOrUri: File | string,
  fileName: string,
  mimeType: string,
  subtopicId?: number
): Promise<UploadedMaterialResponse> {
  const formData = new FormData();

  if (Platform.OS === "web" && fileOrUri instanceof File) {
    formData.append("file", fileOrUri, fileName);
  } else {
    formData.append("file", {
      uri: fileOrUri as string,
      name: fileName,
      type: mimeType,
    } as any);
  }

  if (subtopicId) {
    formData.append("subtopic_id", String(subtopicId));
  }

  const { data } = await apiClient.post<UploadedMaterialResponse>(
    `/uploads/${courseId}`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}
