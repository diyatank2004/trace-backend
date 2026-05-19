import uuid
import enum
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class GlobalRole(str, enum.Enum):
    ADMIN = "Admin"
    USER = "User"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    global_role = Column(Enum(GlobalRole), nullable=False, default=GlobalRole.USER)
    
    employee_id = Column(String(50), unique=True, nullable=True, index=True)
    email = Column(String(254), unique=True, nullable=True, index=True)
    full_name = Column(String(120), nullable=False)
    
    username = Column(String(50), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # FIXED: Added foreign_keys string matching the exact junction table relationship target
    memberships = relationship(
        "ProjectMember", 
        back_populates="user", 
        cascade="all, delete-orphan",
        foreign_keys="[ProjectMember.user_id]"
    )