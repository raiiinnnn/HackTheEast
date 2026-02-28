import apiClient from "./client";
import { CourseResponse } from "./types";

export async function listCourses(): Promise<CourseResponse[]> {
  const { data } = await apiClient.get<CourseResponse[]>("/courses");
  return data;
}

export async function getCourse(courseId: number): Promise<CourseResponse> {
  const { data } = await apiClient.get<CourseResponse>(`/courses/${courseId}`);
  return data;
}

export async function createCourse(
  title: string,
  description?: string
): Promise<CourseResponse> {
  const { data } = await apiClient.post<CourseResponse>("/courses", {
    title,
    description,
  });
  return data;
}

export interface TopicInput {
  title: string;
  order: number;
  subtopics: { title: string; order: number }[];
}

export async function updateSyllabus(
  courseId: number,
  topics: TopicInput[]
): Promise<CourseResponse> {
  const { data } = await apiClient.post<CourseResponse>(
    `/courses/${courseId}/structure`,
    { topics }
  );
  return data;
}
