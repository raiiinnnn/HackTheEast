from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database.session import get_db
from app.models.user import User
from app.models.course import Course, Topic, Subtopic
from app.models.content import QuizItem
from app.models.progress import SubtopicProgress
from app.core.security import get_current_user
from app.schemas.progress import (
    ProgressUpdate,
    SubtopicProgressResponse,
    CourseProgressResponse,
    CadenceUpdate,
)

router = APIRouter(prefix="/progress", tags=["progress"])

CADENCE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


async def _get_or_create_progress(
    db: AsyncSession, user_id: int, subtopic_id: int, course_id: int
) -> SubtopicProgress:
    result = await db.execute(
        select(SubtopicProgress).where(
            SubtopicProgress.user_id == user_id,
            SubtopicProgress.subtopic_id == subtopic_id,
        )
    )
    prog = result.scalar_one_or_none()
    if not prog:
        prog = SubtopicProgress(
            user_id=user_id,
            subtopic_id=subtopic_id,
            course_id=course_id,
        )
        db.add(prog)
        await db.flush()
        await db.refresh(prog)
    return prog


@router.post("/{subtopic_id}")
async def update_progress(
    subtopic_id: int,
    body: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    st = (await db.execute(select(Subtopic).where(Subtopic.id == subtopic_id))).scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Subtopic not found")

    topic = (await db.execute(select(Topic).where(Topic.id == st.topic_id))).scalar_one()
    prog = await _get_or_create_progress(db, user.id, subtopic_id, topic.course_id)

    if body.reel_watched:
        prog.reels_watched = (prog.reels_watched or 0) + 1

    if body.quiz_item_id and body.user_answer:
        qi = (await db.execute(select(QuizItem).where(QuizItem.id == body.quiz_item_id))).scalar_one_or_none()
        if qi:
            is_correct = body.user_answer.strip().lower() == qi.correct_answer.strip().lower()
            prog.total_attempts = (prog.total_attempts or 0) + 1
            if is_correct:
                prog.correct_attempts = (prog.correct_attempts or 0) + 1

            # Simple mastery: weighted ratio of correct answers, boosted by reel engagement
            if prog.total_attempts > 0:
                accuracy = (prog.correct_attempts / prog.total_attempts) * 100
                reel_bonus = min((prog.reels_watched or 0) * 2, 20)
                prog.mastery_score = min(accuracy + reel_bonus, 100.0)

            from app.models.content import QuizResult
            qr = QuizResult(
                user_id=user.id,
                quiz_item_id=qi.id,
                subtopic_id=subtopic_id,
                user_answer=body.user_answer,
                is_correct=1 if is_correct else 0,
            )
            db.add(qr)

            now = datetime.now(timezone.utc)
            prog.last_reviewed_at = now
            interval = CADENCE_INTERVALS.get(prog.review_cadence, timedelta(days=1))
            # Low mastery → more frequent reviews
            if prog.mastery_score < 40:
                interval = interval / 2
            prog.next_review_at = now + interval

            return {
                "is_correct": is_correct,
                "correct_answer": qi.correct_answer,
                "explanation": qi.explanation,
                "mastery_score": prog.mastery_score,
            }

    return {"message": "Progress updated", "mastery_score": prog.mastery_score}


@router.get("/{course_id}", response_model=CourseProgressResponse)
async def get_progress(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id, Course.user_id == user.id)
        .options(selectinload(Course.topics).selectinload(Topic.subtopics))
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    subtopics_data = []
    total_mastery = 0.0
    count = 0

    for topic in course.topics:
        for st in topic.subtopics:
            prog_result = await db.execute(
                select(SubtopicProgress).where(
                    SubtopicProgress.user_id == user.id,
                    SubtopicProgress.subtopic_id == st.id,
                )
            )
            prog = prog_result.scalar_one_or_none()
            mastery = prog.mastery_score if prog else 0.0
            total_mastery += mastery
            count += 1

            subtopics_data.append(
                SubtopicProgressResponse(
                    subtopic_id=st.id,
                    subtopic_title=st.title,
                    topic_title=topic.title,
                    mastery_score=mastery,
                    total_attempts=prog.total_attempts if prog else 0,
                    correct_attempts=prog.correct_attempts if prog else 0,
                    reels_watched=prog.reels_watched if prog else 0,
                    review_cadence=prog.review_cadence if prog else "daily",
                    last_reviewed_at=prog.last_reviewed_at if prog else None,
                    next_review_at=prog.next_review_at if prog else None,
                )
            )

    overall = (total_mastery / count) if count > 0 else 0.0

    return CourseProgressResponse(
        course_id=course_id,
        overall_mastery=overall,
        subtopics=subtopics_data,
    )


@router.put("/{subtopic_id}/cadence")
async def update_cadence(
    subtopic_id: int,
    body: CadenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    st = (await db.execute(select(Subtopic).where(Subtopic.id == subtopic_id))).scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Subtopic not found")

    topic = (await db.execute(select(Topic).where(Topic.id == st.topic_id))).scalar_one()
    prog = await _get_or_create_progress(db, user.id, subtopic_id, topic.course_id)
    prog.review_cadence = body.review_cadence

    now = datetime.now(timezone.utc)
    interval = CADENCE_INTERVALS.get(body.review_cadence, timedelta(days=1))
    prog.next_review_at = now + interval

    return {"message": "Cadence updated", "review_cadence": prog.review_cadence}
