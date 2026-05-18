from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.models import User, GlobalRole
from app.auth.schemas import (
    AdminSignupRequest, AdminLoginRequest, 
    UserOnboardingRequest, UserResponse, TokenResponse
)
from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user

# Declaring the prefix clean
router = APIRouter(prefix="/auth", tags=["Identity & Profiles"])

# --- Admin Account Creation (One-time setup path) ---
@router.post("/admin/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_signup(data: AdminSignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Admin username is already taken.")
        
    new_admin = User(
        username=data.username,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        global_role=GlobalRole.ADMIN
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin


# --- Admin Session Login (Generates token to authorize administrative routes) ---
@router.post("/admin/login", response_model=TokenResponse)
def admin_login(data: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(User).filter(User.username == data.username, User.global_role == GlobalRole.ADMIN).first()
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid admin credentials.")
        
    token = create_access_token({"sub": str(admin.id), "role": admin.global_role.value})
    return {"access_token": token, "token_type": "bearer"}


# --- Team Leader & Member Profile Save Path (Identified uniquely by Employee ID with NO passwords) ---
@router.post("/user/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def user_onboarding(data: UserOnboardingRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.employee_id == data.employee_id).first():
        raise HTTPException(status_code=400, detail="Employee ID already registered in the platform database.")
        
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email address already registered.")

    new_employee = User(
        employee_id=data.employee_id,
        email=data.email,
        full_name=data.full_name,
        global_role=GlobalRole.USER
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee


# --- FIXED SECURED ADMIN ROUTE: Completely delete a User record (Member/TL) from the whole application ---
@router.delete("/admin/delete-user/{employee_id}", status_code=status.HTTP_200_OK)
def admin_permanently_delete_user(
    employee_id: str, 
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_user)  # Extract securely from headers
):
    # 1. Gatekeep Check: Verify role privilege tier
    if current_admin.global_role != GlobalRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access Denied. Only system administrators can completely remove user accounts."
        )

    # 2. Check if admin is trying to delete themselves via employee id path mixups
    if current_admin.employee_id == employee_id and employee_id is not None:
        raise HTTPException(status_code=400, detail="Administrative accounts cannot self-terminate via user management gates.")

    # 3. Query target employee profile
    target_user = db.query(User).filter(User.employee_id == employee_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user account matching Employee ID not found.")

    # 4. Trigger deletion (On-delete Cascade clears related workspace association entries automatically)
    db.delete(target_user)
    db.commit()

    return {
        "status": "success",
        "message": f"User account associated with employee_id '{employee_id}' has been permanently wiped from FlowForge."
    }