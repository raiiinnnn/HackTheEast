import apiClient from "./client";
import { CourseProgressResponse } from "./types";

export async function submitProgress(
  subtopicId: number,
  payload: {
    quiz_item_id?: number;
    user_answer?: string;
    reel_watched?: boolean;
  }
): Promise<any> {
  const { data } = await apiClient.post(`/progress/${subtopicId}`, payload);
  return data;
}

export async function getCourseProgress(
  courseId: number
): Promise<CourseProgressResponse> {
  const { data } = await apiClient.get<CourseProgressResponse>(
    `/progress/${courseId}`
  );
  return data;
}

export async function updateCadence(
  subtopicId: number,
  cadence: string
): Promise<any> {
  const { data } = await apiClient.put(`/progress/${subtopicId}/cadence`, {
    review_cadence: cadence,
  });
  return data;
}
