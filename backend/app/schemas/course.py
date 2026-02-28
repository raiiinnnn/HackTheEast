from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class SubtopicCreate(BaseModel):
    title: str
    order: int = 0


class SubtopicResponse(BaseModel):
    id: int
    topic_id: int
    title: str
    order: int

    class Config:
        from_attributes = True


class TopicCreate(BaseModel):
    title: str
    order: int = 0
    subtopics: List[SubtopicCreate] = []


class TopicResponse(BaseModel):
    id: int
    course_id: int
    title: str
    order: int
    subtopics: List[SubtopicResponse] = []

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None


class CourseResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    topics: List[TopicResponse] = []

    class Config:
        from_attributes = True


class SyllabusCreate(BaseModel):
    topics: List[TopicCreate]


class CanvasImportRequest(BaseModel):
    canvas_base_url: str
    canvas_api_token: str
    canvas_course_id: str
