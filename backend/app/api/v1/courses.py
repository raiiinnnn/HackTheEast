from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from app.database.session import get_db
from app.models.user import User
from app.models.course import Course, Topic, Subtopic
from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    SyllabusCreate,
    CanvasImportRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course = Course(user_id=user.id, title=body.title, description=body.description)
    db.add(course)
    await db.flush()

    result = await db.execute(
        select(Course)
        .where(Course.id == course.id)
        .options(selectinload(Course.topics).selectinload(Topic.subtopics))
    )
    return result.scalar_one()


@router.get("", response_model=List[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Course)
        .where(Course.user_id == user.id)
        .options(selectinload(Course.topics).selectinload(Topic.subtopics))
        .order_by(Course.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
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
    return course


@router.post("/{course_id}/structure", response_model=CourseResponse)
async def update_syllabus(
    course_id: int,
    body: SyllabusCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    for t in body.topics:
        topic = Topic(course_id=course.id, title=t.title, order=t.order)
        db.add(topic)
        await db.flush()
        await db.refresh(topic)
        for s in t.subtopics:
            subtopic = Subtopic(topic_id=topic.id, title=s.title, order=s.order)
            db.add(subtopic)

    await db.flush()

    refreshed = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.topics).selectinload(Topic.subtopics))
    )
    return refreshed.scalar_one()


@router.post("/import/canvas")
async def import_canvas(body: CanvasImportRequest):
    # TODO: Implement Canvas LMS API integration
    # 1. Use body.canvas_api_token to authenticate with Canvas
    # 2. Fetch course modules from body.canvas_base_url/api/v1/courses/{canvas_course_id}/modules
    # 3. For each module, fetch items and map them to topics/subtopics
    # 4. Create the course structure in our DB
    return {
        "message": "Canvas import is not yet implemented. This endpoint will accept Canvas LMS credentials and automatically import course structure.",
        "status": "stub",
    }
