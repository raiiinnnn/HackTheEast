from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, func
from app.database.base import Base


class SubtopicProgress(Base):
    """Tracks per-user mastery of each subtopic (0–100).
    The spaced-repetition scheduler uses `mastery_score` and `review_cadence`
    to decide which subtopics to surface next. A production system would
    store per-review intervals (SM-2 or similar); this simplified model
    uses a single score with a configurable cadence."""

    __tablename__ = "subtopic_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    mastery_score = Column(Float, default=0.0)  # 0-100
    total_attempts = Column(Integer, default=0)
    correct_attempts = Column(Integer, default=0)
    reels_watched = Column(Integer, default=0)
    review_cadence = Column(String(20), default="daily")  # daily, weekly, custom
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    next_review_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
