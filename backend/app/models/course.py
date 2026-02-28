from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.database.base import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    topics = relationship("Topic", back_populates="course", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="topics")
    subtopics = relationship("Subtopic", back_populates="topic", cascade="all, delete-orphan")


class Subtopic(Base):
    __tablename__ = "subtopics"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    topic = relationship("Topic", back_populates="subtopics")
