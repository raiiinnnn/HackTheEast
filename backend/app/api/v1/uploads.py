import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database.session import get_db
from app.models.user import User
from app.models.content import UploadedMaterial
from app.core.security import get_current_user
from app.schemas.content import UploadedMaterialResponse
from app.services.storage import upload_file_to_s3

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "video/mp4": "mp4",
    "video/quicktime": "mp4",
}


@router.post("/{course_id}", response_model=UploadedMaterialResponse, status_code=201)
async def upload_material(
    course_id: int,
    file: UploadFile = File(...),
    subtopic_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    content_type = file.content_type or ""
    file_type = ALLOWED_TYPES.get(content_type)
    if not file_type:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Allowed: PDF, PPTX, MP4",
        )

    file_bytes = await file.read()
    s3_key = f"courses/{course_id}/{uuid.uuid4().hex}_{file.filename}"

    s3_url = await upload_file_to_s3(file_bytes, s3_key, content_type)

    material = UploadedMaterial(
        course_id=course_id,
        subtopic_id=subtopic_id,
        user_id=user.id,
        filename=file.filename or "unknown",
        file_type=file_type,
        s3_key=s3_key,
        s3_url=s3_url,
    )
    db.add(material)
    await db.flush()
    await db.refresh(material)
    return material
