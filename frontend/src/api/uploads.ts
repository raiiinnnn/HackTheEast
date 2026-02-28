import apiClient from "./client";
import { UploadedMaterialResponse } from "./types";

export async function uploadMaterial(
  courseId: number,
  fileUri: string,
  fileName: string,
  mimeType: string,
  subtopicId?: number
): Promise<UploadedMaterialResponse> {
  const formData = new FormData();
  formData.append("file", {
    uri: fileUri,
    name: fileName,
    type: mimeType,
  } as any);
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
