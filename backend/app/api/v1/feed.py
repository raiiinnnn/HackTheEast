from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database.session import get_db
from app.models.user import User
from app.models.content import Reel, QuizItem
from app.core.security import get_current_user
from app.schemas.content import (
    FeedResponse,
    FeedReelItem,
    FeedQuizItem,
    ReelResponse,
    QuizItemResponse,
)

router = APIRouter(prefix="/feed", tags=["feed"])

QUIZ_INSERT_INTERVAL = 3


@router.get("/{course_id}", response_model=FeedResponse)
async def get_feed(
    course_id: int,
    subtopic_id: Optional[int] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reel_query = select(Reel).where(Reel.course_id == course_id).order_by(Reel.order)
    if subtopic_id:
        reel_query = reel_query.where(Reel.subtopic_id == subtopic_id)
    reels = (await db.execute(reel_query)).scalars().all()

    quiz_query = select(QuizItem).where(QuizItem.course_id == course_id)
    if subtopic_id:
        quiz_query = quiz_query.where(QuizItem.subtopic_id == subtopic_id)
    quizzes = (await db.execute(quiz_query)).scalars().all()

    items = []
    quiz_idx = 0
    for i, reel in enumerate(reels):
        items.append(
            FeedReelItem(
                reel=ReelResponse(
                    id=reel.id,
                    course_id=reel.course_id,
                    subtopic_id=reel.subtopic_id,
                    title=reel.title,
                    script=reel.script,
                    captions=reel.captions,
                    duration_seconds=reel.duration_seconds,
                    media_urls=reel.media_urls,
                    audio_url=reel.audio_url,
                    thumbnail_url=reel.thumbnail_url,
                    order=reel.order,
                )
            )
        )
        if (i + 1) % QUIZ_INSERT_INTERVAL == 0 and quiz_idx < len(quizzes):
            q = quizzes[quiz_idx]
            items.append(
                FeedQuizItem(
                    quiz=QuizItemResponse(
                        id=q.id,
                        course_id=q.course_id,
                        subtopic_id=q.subtopic_id,
                        question=q.question,
                        question_type=q.question_type,
                        options=q.options,
                        difficulty=q.difficulty,
                    )
                )
            )
            quiz_idx += 1

    total = len(items)
    items = items[offset : offset + limit]

    return FeedResponse(items=items, course_id=course_id, total=total)
