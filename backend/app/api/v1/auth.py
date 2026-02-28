import secrets
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    GoogleAuthRequest,
    AbelianRegisterRequest,
    AbelianChallengeRequest,
    AbelianChallengeResponse,
    AbelianVerifyRequest,
)
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory nonce store: crypto_address -> challenge
_abelian_challenges: Dict[str, str] = {}


# ---------- Email + Password ----------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


# ---------- Google OAuth ----------

@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        idinfo = google_id_token.verify_oauth2_token(
            body.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    google_sub = idinfo["sub"]
    email = idinfo.get("email")
    name = idinfo.get("name")

    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        if email:
            result2 = await db.execute(select(User).where(User.email == email))
            user = result2.scalar_one_or_none()
            if user:
                user.google_id = google_sub
                user.auth_provider = "google"
                await db.flush()

    if not user:
        user = User(
            email=email,
            display_name=name,
            auth_provider="google",
            google_id=google_sub,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


# ---------- Abelian Wallet ----------

@router.post("/abelian/generate")
async def abelian_generate():
    """Proxy to the Go Abelian service to generate a new keypair."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(f"{settings.ABELIAN_SERVICE_URL}/keys/generate")
            resp.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Abelian service unavailable")
    return resp.json()


@router.post("/abelian/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def abelian_register(body: AbelianRegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(User).where(User.abelian_address == body.crypto_address)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Wallet already registered")

    user = User(
        display_name=body.display_name,
        auth_provider="abelian",
        abelian_address=body.crypto_address,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/abelian/challenge", response_model=AbelianChallengeResponse)
async def abelian_challenge(body: AbelianChallengeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.abelian_address == body.crypto_address)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Wallet not registered")

    challenge = secrets.token_hex(32)
    _abelian_challenges[body.crypto_address] = challenge
    return AbelianChallengeResponse(challenge=challenge)


@router.post("/abelian/verify", response_model=TokenResponse)
async def abelian_verify(body: AbelianVerifyRequest, db: AsyncSession = Depends(get_db)):
    expected = _abelian_challenges.pop(body.crypto_address, None)
    if not expected or expected != body.challenge:
        raise HTTPException(status_code=401, detail="Invalid or expired challenge")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.ABELIAN_SERVICE_URL}/verify",
                json={
                    "message": body.challenge,
                    "signature": body.signature,
                    "crypto_address": body.crypto_address,
                },
            )
            resp.raise_for_status()
            result = resp.json()
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="Abelian service unavailable")

    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid signature")

    db_result = await db.execute(
        select(User).where(User.abelian_address == body.crypto_address)
    )
    user = db_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Wallet not registered")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


# ---------- Current User ----------

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
