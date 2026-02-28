from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.models.user import User
from app.models.course import Course, Subtopic
from app.models.content import UploadedMaterial, Reel, ConceptCard, QuizItem
from app.core.security import get_current_user
from app.schemas.content import GenerateRequest, GenerateResponse
from app.services.content_processing import extract_text_from_material
from app.services.minimax_service import (
    generate_concept_cards,
    generate_reel_scripts,
    generate_quiz_items,
)

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/{course_id}", response_model=GenerateResponse)
async def generate_content(
    course_id: int,
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    mat_query = select(UploadedMaterial).where(UploadedMaterial.course_id == course_id)
    if body.subtopic_id:
        mat_query = mat_query.where(UploadedMaterial.subtopic_id == body.subtopic_id)
    materials = (await db.execute(mat_query)).scalars().all()

    if not materials:
        raise HTTPException(status_code=400, detail="No uploaded materials found for this course")

    combined_text = ""
    for mat in materials:
        text = await extract_text_from_material(mat)
        if text:
            combined_text += f"\n\n--- {mat.filename} ---\n{text}"
            mat.extracted_text = text

    if not combined_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from materials")

    subtopic_title = None
    if body.subtopic_id:
        st = (await db.execute(select(Subtopic).where(Subtopic.id == body.subtopic_id))).scalar_one_or_none()
        subtopic_title = st.title if st else None

    topic_metadata = {
        "course_title": course.title,
        "subtopic_id": body.subtopic_id,
        "subtopic_title": subtopic_title,
    }

    cards_data = await generate_concept_cards(combined_text, topic_metadata)
    reels_data = await generate_reel_scripts(combined_text, body.reel_duration, topic_metadata)
    quiz_data = await generate_quiz_items(combined_text, "medium", 5, topic_metadata)

    reels_created = 0
    for i, r in enumerate(reels_data):
        reel = Reel(
            course_id=course_id,
            subtopic_id=body.subtopic_id,
            title=r["title"],
            script=r["script"],
            captions=r.get("captions"),
            duration_seconds=body.reel_duration,
            media_urls=r.get("media_urls"),
            audio_url=r.get("audio_url"),
            order=i,
        )
        db.add(reel)
        reels_created += 1

    cards_created = 0
    for c in cards_data:
        card = ConceptCard(
            course_id=course_id,
            subtopic_id=body.subtopic_id,
            title=c["title"],
            content=c["content"],
            card_type=c.get("card_type", "definition"),
        )
        db.add(card)
        cards_created += 1

    quizzes_created = 0
    for q in quiz_data:
        qi = QuizItem(
            course_id=course_id,
            subtopic_id=body.subtopic_id,
            question=q["question"],
            question_type=q.get("question_type", "mcq"),
            options=q.get("options"),
            correct_answer=q["correct_answer"],
            explanation=q.get("explanation"),
            difficulty=q.get("difficulty", "medium"),
        )
        db.add(qi)
        quizzes_created += 1

    await db.flush()

    return GenerateResponse(
        reels_created=reels_created,
        concept_cards_created=cards_created,
        quiz_items_created=quizzes_created,
        message="Content generated successfully",
    )
