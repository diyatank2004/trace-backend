from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.auth.models import GlobalRole

class AdminSignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=120)

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# NEW: Comprehensive Onboarding Form Contract
class EmployeeOnboardingRequest(BaseModel):
    employee_id: str = Field(..., min_length=2, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone_number: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    skills: Optional[str] = Field(None, description="Comma-separated string tags")

class EmployeeResponse(BaseModel):
    id: UUID
    global_role: GlobalRole
    employee_id: Optional[str]
    full_name: str
    email: Optional[str]
    department: Optional[str]
    designation: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True