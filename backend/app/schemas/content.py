from pydantic import BaseModel
from typing import Optional, List, Any, Literal, Union
from datetime import datetime


class UploadedMaterialResponse(BaseModel):
    id: int
    course_id: int
    subtopic_id: Optional[int] = None
    filename: str
    file_type: str
    s3_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReelResponse(BaseModel):
    id: int
    course_id: int
    subtopic_id: Optional[int] = None
    title: str
    script: str
    captions: Optional[str] = None
    duration_seconds: int
    media_urls: Optional[List[str]] = None
    audio_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    order: int

    class Config:
        from_attributes = True


class ConceptCardResponse(BaseModel):
    id: int
    course_id: int
    subtopic_id: Optional[int] = None
    title: str
    content: str
    card_type: str

    class Config:
        from_attributes = True


class QuizItemResponse(BaseModel):
    id: int
    course_id: int
    subtopic_id: Optional[int] = None
    question: str
    question_type: str
    options: Optional[List[str]] = None
    difficulty: str

    class Config:
        from_attributes = True


class QuizItemWithAnswer(QuizItemResponse):
    correct_answer: str
    explanation: Optional[str] = None


class QuizSubmission(BaseModel):
    quiz_item_id: int
    user_answer: str


class QuizResultResponse(BaseModel):
    quiz_item_id: int
    is_correct: bool
    correct_answer: str
    explanation: Optional[str] = None


class FeedReelItem(BaseModel):
    type: Literal["reel"] = "reel"
    reel: ReelResponse


class FeedQuizItem(BaseModel):
    type: Literal["quiz"] = "quiz"
    quiz: QuizItemResponse


FeedItem = Union[FeedReelItem, FeedQuizItem]


class FeedResponse(BaseModel):
    items: List[FeedItem]
    course_id: int
    total: int


class GenerateRequest(BaseModel):
    subtopic_id: Optional[int] = None
    reel_duration: int = 30  # 15, 30, or 60


class GenerateResponse(BaseModel):
    reels_created: int
    concept_cards_created: int
    quiz_items_created: int
    message: str
