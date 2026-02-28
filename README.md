# FocusFeed

A full-stack iOS-first learning app that turns course materials into TikTok/Reels-style short videos, quizzes, and an adaptive Focus Feed using MiniMax AI.

## Architecture

```
/frontend        # Expo (React Native + TypeScript) mobile app
/backend         # FastAPI (Python 3.11+) backend
docker-compose.yml
```

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (for database + object storage)
- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **Expo CLI**: `npm install -g expo-cli`

### 1. Set up environment

```bash
cp .env.example .env
# Edit .env and set your MINIMAX_API_KEY
```

### 2. Start infrastructure (PostgreSQL + MinIO)

```bash
docker-compose up -d db minio
```

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000. Interactive docs at http://localhost:8000/docs.

### 4. Start the frontend

```bash
cd frontend
npm install
npx expo start
```

Scan the QR code with Expo Go, or press `i` for iOS simulator.

### Using Make

```bash
make up               # Start all Docker services
make backend-dev      # Run backend with hot reload
make backend-migrate  # Run Alembic migrations
make frontend-dev     # Start Expo dev server
```

## Project Structure

### Backend (`/backend`)

```
app/
├── main.py              # FastAPI app entry point
├── api/v1/
│   ├── auth.py          # Register, login, JWT
│   ├── courses.py       # CRUD courses, syllabus, Canvas stub
│   ├── uploads.py       # File upload (PDF/PPTX/MP4)
│   ├── generate.py      # AI content generation pipeline
│   ├── feed.py          # Focus Feed (reels + quizzes)
│   └── progress.py      # Mastery tracking, spaced repetition
├── core/
│   ├── config.py        # Settings from env vars
│   └── security.py      # JWT auth, password hashing
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic request/response schemas
├── services/
│   ├── minimax_service.py     # MiniMax LLM/TTS integration
│   ├── content_processing.py  # PDF/PPTX/video text extraction
│   └── storage.py             # S3-compatible storage abstraction
└── database/
    ├── base.py          # SQLAlchemy declarative base
    └── session.py       # Async session factory
```

### Frontend (`/frontend`)

```
app/
├── _layout.tsx          # Root layout (Stack navigator)
├── index.tsx            # Entry redirect (auth check)
├── (auth)/
│   ├── login.tsx        # Login screen
│   └── register.tsx     # Registration screen
├── (tabs)/
│   ├── index.tsx        # Course list
│   └── profile.tsx      # User profile
└── course/
    └── [id].tsx         # Course detail with tabs

src/
├── api/                 # Typed API client functions
├── store/               # Zustand state (auth, app)
├── components/          # Tab components (Syllabus, Upload, Feed, Progress)
└── constants/           # Theme, API config
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get JWT |
| GET | `/api/v1/auth/me` | Get current user |
| GET/POST | `/api/v1/courses` | List/create courses |
| POST | `/api/v1/courses/{id}/structure` | Add syllabus topics |
| POST | `/api/v1/courses/import/canvas` | Canvas LMS import (stub) |
| POST | `/api/v1/uploads/{course_id}` | Upload PDF/PPTX/MP4 |
| POST | `/api/v1/generate/{course_id}` | Generate AI content |
| GET | `/api/v1/feed/{course_id}` | Get Focus Feed items |
| POST | `/api/v1/progress/{subtopic_id}` | Submit quiz/reel progress |
| GET | `/api/v1/progress/{course_id}` | Get mastery per subtopic |

## MiniMax Integration

The MiniMax API key is read from `MINIMAX_API_KEY` in `.env`. The service module at `backend/app/services/minimax_service.py` exposes:

- `generate_concept_cards()` — extracts key concepts as flashcards
- `generate_reel_scripts()` — creates short, engaging video scripts
- `generate_quiz_items()` — generates MCQ quiz questions
- `generate_voice_narration()` — TTS via MiniMax speech API

All functions fall back to local stub generators if the API is unavailable, enabling offline development.

## Key Design Decisions

- **Spaced repetition**: Simplified mastery-score model (0–100) with configurable daily/weekly cadence. Low-mastery subtopics get reviewed more frequently.
- **Video pipeline**: Reel metadata (scripts, captions, visual notes) is generated first. Actual video composition is a clear placeholder — plug in ffmpeg/remotion pipeline later.
- **S3 abstraction**: Storage uses boto3 with configurable endpoint URL, making it easy to swap between MinIO (local), AWS S3, Cloudflare R2, etc.
- **Feed interleaving**: Quiz cards are inserted every N reels (default 3) to reinforce learning while scrolling.
