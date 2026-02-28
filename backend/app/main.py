import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.courses import router as courses_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.generate import router as generate_router
from app.api.v1.feed import router as feed_router
from app.api.v1.progress import router as progress_router

logger = logging.getLogger(__name__)

# Ensure CORS origins is always a list (env may pass JSON string)
_cors_origins: list = list(settings.BACKEND_CORS_ORIGINS) if settings.BACKEND_CORS_ORIGINS else ["http://localhost:8082", "http://localhost:8081", "http://localhost:19006"]

app = FastAPI(
    title="FocusFeed API",
    description="Turn course materials into TikTok-style learning reels, quizzes, and an adaptive Focus Feed.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Ensure 500 and other unhandled errors still return CORS headers (via middleware) and a proper body."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
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
