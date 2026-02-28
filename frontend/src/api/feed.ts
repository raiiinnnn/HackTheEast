import apiClient from "./client";
import { FeedResponse } from "./types";

export async function getFeed(
  courseId: number,
  subtopicId?: number,
  offset: number = 0,
  limit: number = 20
): Promise<FeedResponse> {
  const params: Record<string, any> = { offset, limit };
  if (subtopicId) params.subtopic_id = subtopicId;
  const { data } = await apiClient.get<FeedResponse>(`/feed/${courseId}`, {
    params,
  });
  return data;
}
