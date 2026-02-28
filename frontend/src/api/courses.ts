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

export async function deleteTopic(
  courseId: number,
  topicId: number
): Promise<void> {
  await apiClient.delete(`/courses/${courseId}/topics/${topicId}`);
}

export interface ParsedSyllabusTopic {
  topic: string;
  subtopics: string[];
  weight: number;
}

export interface ParsedSyllabusResponse {
  course_name: string;
  topics: ParsedSyllabusTopic[];
}

export async function parseSyllabusPdf(
  file: File,
  courseContext?: string
): Promise<ParsedSyllabusResponse> {
  const formData = new FormData();
  formData.append("file", file, file.name);
  if (courseContext) {
    formData.append("course_context", courseContext);
  }
  const { data } = await apiClient.post<ParsedSyllabusResponse>(
    "/courses/syllabus/parse",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}
