import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class ProjectRole(str, enum.Enum):
    TEAM_LEADER = "Team Leader"
    MEMBER = "Member"

class ProjectMember(Base):
    __tablename__ = "project_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    
    role = Column(Enum(ProjectRole), nullable=False)
    employee_id = Column(String(50), ForeignKey("users.employee_id", ondelete="CASCADE"), nullable=False)  
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Explicit mapping definitions targeting column variables
    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    project = relationship("Project", back_populates="members", foreign_keys=[project_id])

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # WS_id
    name = Column(String(120), nullable=False)
    slug = Column(String(40), unique=True, nullable=False, index=True)
    project_key = Column(String(20), unique=True, nullable=False, index=True)
    created_on = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members = relationship(
        "ProjectMember", 
        back_populates="project", 
        cascade="all, delete-orphan",
        foreign_keys="[ProjectMember.project_id]"
    )