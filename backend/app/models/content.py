from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, JSON, func
from app.database.base import Base


class UploadedMaterial(Base):
    __tablename__ = "uploaded_materials"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, pptx, mp4
    s3_key = Column(String(500), nullable=False)
    s3_url = Column(String(1000), nullable=True)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Reel(Base):
    __tablename__ = "reels"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    script = Column(Text, nullable=False)
    captions = Column(Text, nullable=True)
    duration_seconds = Column(Integer, default=30)
    media_urls = Column(JSON, nullable=True)  # list of URLs for images/video/audio
    audio_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ConceptCard(Base):
    __tablename__ = "concept_cards"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    card_type = Column(String(50), default="definition")  # definition, formula, key_idea
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuizItem(Base):
    __tablename__ = "quiz_items"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    question_type = Column(String(20), default="mcq")  # mcq, short_answer
    options = Column(JSON, nullable=True)  # list of option strings for MCQ
    correct_answer = Column(String(500), nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_item_id = Column(Integer, ForeignKey("quiz_items.id"), nullable=False)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True, index=True)
    user_answer = Column(String(500), nullable=False)
    is_correct = Column(Integer, default=0)  # 0 or 1
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
