export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  display_name: string | null;
}

export interface SubtopicResponse {
  id: number;
  topic_id: number;
  title: string;
  order: number;
}

export interface TopicResponse {
  id: number;
  course_id: number;
  title: string;
  order: number;
  subtopics: SubtopicResponse[];
}

export interface CourseResponse {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  created_at: string;
  topics: TopicResponse[];
}

export interface UploadedMaterialResponse {
  id: number;
  course_id: number;
  subtopic_id: number | null;
  filename: string;
  file_type: string;
  s3_url: string | null;
  created_at: string;
}

export interface ReelResponse {
  id: number;
  course_id: number;
  subtopic_id: number | null;
  title: string;
  script: string;
  captions: string | null;
  duration_seconds: number;
  media_urls: string[] | null;
  audio_url: string | null;
  thumbnail_url: string | null;
  order: number;
}

export interface QuizItemResponse {
  id: number;
  course_id: number;
  subtopic_id: number | null;
  question: string;
  question_type: string;
  options: string[] | null;
  difficulty: string;
}

export interface FeedReelItem {
  type: "reel";
  reel: ReelResponse;
}

export interface FeedQuizItem {
  type: "quiz";
  quiz: QuizItemResponse;
}

export type FeedItem = FeedReelItem | FeedQuizItem;

export interface FeedResponse {
  items: FeedItem[];
  course_id: number;
  total: number;
}

export interface GenerateResponse {
  reels_created: number;
  concept_cards_created: number;
  quiz_items_created: number;
  message: string;
}

export interface SubtopicProgressResponse {
  subtopic_id: number;
  subtopic_title: string;
  topic_title: string;
  mastery_score: number;
  total_attempts: number;
  correct_attempts: number;
  reels_watched: number;
  review_cadence: string;
  last_reviewed_at: string | null;
  next_review_at: string | null;
}

export interface CourseProgressResponse {
  course_id: number;
  overall_mastery: number;
  subtopics: SubtopicProgressResponse[];
}
