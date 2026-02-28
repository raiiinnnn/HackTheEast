from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func
from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    auth_provider = Column(String(20), nullable=False, default="email")
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    abelian_address = Column(Text, nullable=True)
    video_duration_pref = Column(String(10), nullable=False, server_default="medium")
    reel_types_pref = Column(JSON, nullable=False, server_default='["clips"]')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
