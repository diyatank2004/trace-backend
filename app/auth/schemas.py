from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.auth.models import GlobalRole

# --- Admin Traditional Authenticators ---
class AdminSignupRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str

class AdminLoginRequest(BaseModel):
    username: str
    password: str

# --- Team Leader & Member Registration Schema (No Passwords!) ---
class UserOnboardingRequest(BaseModel):
    employee_id: str = Field(..., description="Unique Corporate Employee ID Token")
    email: EmailStr
    full_name: str

# --- Output Transport Structures ---
class UserResponse(BaseModel):
    id: UUID
    global_role: GlobalRole
    employee_id: Optional[str] = None
    email: Optional[str] = None
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str