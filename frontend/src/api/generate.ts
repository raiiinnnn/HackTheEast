import apiClient from "./client";
import { GenerateResponse } from "./types";

export async function generateContent(
  courseId: number,
  subtopicId?: number,
  reelDuration: number = 30
): Promise<GenerateResponse> {
  const { data } = await apiClient.post<GenerateResponse>(
    `/generate/${courseId}`,
    { subtopic_id: subtopicId, reel_duration: reelDuration }
  );
  return data;
}
