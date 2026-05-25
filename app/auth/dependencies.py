import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.config import settings
from app.auth.models import Employee

security_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme), 
    db: Session = Depends(get_db)
) -> Employee:
    exception_rule = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalid or credentials expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    
    try:
        # Decode the secure cryptographic signature envelope
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise exception_rule
        user_id = UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise exception_rule
        
    # Query database to confirm the user profile remains active and un-deleted
    user = db.query(Employee).filter(Employee.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account profile associated with this session token no longer exists."
        )
        
    user.active_project_id = payload.get("project_id")
    user.active_project_role = payload.get("project_role")
    
    return user