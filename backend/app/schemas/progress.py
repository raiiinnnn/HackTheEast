from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProgressUpdate(BaseModel):
    quiz_item_id: Optional[int] = None
    user_answer: Optional[str] = None
    reel_watched: bool = False


class SubtopicProgressResponse(BaseModel):
    subtopic_id: int
    subtopic_title: str
    topic_title: str
    mastery_score: float
    total_attempts: int
    correct_attempts: int
    reels_watched: int
    review_cadence: str
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None


class CourseProgressResponse(BaseModel):
    course_id: int
    overall_mastery: float
    subtopics: List[SubtopicProgressResponse]


class CadenceUpdate(BaseModel):
    review_cadence: str  # daily, weekly
