from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.database.session import get_db
from app.models.user import User
from app.models.course import Course, Topic, Subtopic
from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    SyllabusCreate,
    SyllabusParseResponse,
    CanvasImportRequest,
)
from app.core.security import get_current_user
from app.services.bedrock_syllabus_service import parse_syllabus_pdf

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


@router.post(
    "/syllabus/parse",
    response_model=SyllabusParseResponse,
    summary="Parse a syllabus PDF into structured topics/subtopics",
    description="Upload a course syllabus PDF. Amazon Bedrock (Claude 3.5 Sonnet) extracts "
    "the course name, topics, subtopics, and estimated weights as structured JSON.",
)
async def parse_syllabus(
    file: UploadFile = File(..., description="Syllabus PDF file"),
    course_context: Optional[str] = Form(None, description="Optional extra context about the course"),
    user: User = Depends(get_current_user),
):
    if not file.content_type or "pdf" not in file.content_type:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = await parse_syllabus_pdf(pdf_bytes, course_context)
        return SyllabusParseResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bedrock API error: {e}")


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


@router.delete("/{course_id}/topics/{topic_id}", status_code=200)
async def delete_topic(
    course_id: int,
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Course not found")

    topic_result = await db.execute(
        select(Topic).where(Topic.id == topic_id, Topic.course_id == course_id)
    )
    topic = topic_result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    await db.execute(
        select(Subtopic).where(Subtopic.topic_id == topic_id)
    )
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(Subtopic).where(Subtopic.topic_id == topic_id))
    await db.execute(sql_delete(Topic).where(Topic.id == topic_id))
    await db.flush()

    return {"message": "Topic deleted"}


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
