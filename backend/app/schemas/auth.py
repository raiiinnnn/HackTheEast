from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str | None = None
    display_name: str | None = None
    auth_provider: str = "email"
    abelian_address: str | None = None
    video_duration_pref: str = "medium"

    class Config:
        from_attributes = True


class UpdatePreferencesRequest(BaseModel):
    video_duration_pref: str  # "short", "medium", "long"


# --- Google OAuth ---

class GoogleAuthRequest(BaseModel):
    id_token: str


# --- Abelian Wallet ---

class AbelianRegisterRequest(BaseModel):
    crypto_address: str
    display_name: str | None = None


class AbelianChallengeRequest(BaseModel):
    crypto_address: str


class AbelianChallengeResponse(BaseModel):
    challenge: str


class AbelianVerifyRequest(BaseModel):
    crypto_address: str
    challenge: str
    signature: str
