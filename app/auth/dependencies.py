import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
from app.database import get_db
from app.config import settings
from app.auth.models import Employee

# FIXED: Change OAuth2PasswordBearer to HTTPBearer so Swagger expects a raw token header
security_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme), 
    db: Session = Depends(get_db)
) -> Employee:
    """Decodes the incoming Authorization Bearer token header to find the active Admin profile."""
    exception_rule = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalid or credentials expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract the raw token payload string
    token = credentials.credentials
    
    try:
        # Decode token payload using our signature keys
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise exception_rule
        user_id = UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise exception_rule
        
    # Query database to confirm user validity
    user = db.query(Employee).filter(Employee.id == user_id).first()
    if not user:
        raise exception_rule
    return user