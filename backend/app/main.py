from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.generate import router as generate_router
from app.api.v1.feed import router as feed_router
from app.api.v1.progress import router as progress_router

app = FastAPI(
    title="FocusFeed API",
    description="Turn course materials into TikTok-style learning reels, quizzes, and an adaptive Focus Feed.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(courses_router, prefix=PREFIX)
app.include_router(uploads_router, prefix=PREFIX)
app.include_router(generate_router, prefix=PREFIX)
app.include_router(feed_router, prefix=PREFIX)
app.include_router(progress_router, prefix=PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}
