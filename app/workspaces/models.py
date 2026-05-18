import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class WorkspaceRole(str, enum.Enum):
    TEAM_LEADER = "Team Leader"
    MEMBER = "Member"

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    
    role = Column(Enum(WorkspaceRole), nullable=False)
    employee_id = Column(String(50), ForeignKey("users.employee_id", ondelete="CASCADE"), nullable=False)  
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Explicit mapping definitions targeting column variables
    user = relationship("User", back_populates="memberships", foreign_keys=[user_id])
    workspace = relationship("Workspace", back_populates="members", foreign_keys=[workspace_id])

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # WS_id
    name = Column(String(120), nullable=False)
    slug = Column(String(40), unique=True, nullable=False, index=True)
    workspace_key = Column(String(20), unique=True, nullable=False, index=True)
    created_on = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members = relationship(
        "WorkspaceMember", 
        back_populates="workspace", 
        cascade="all, delete-orphan",
        foreign_keys="[WorkspaceMember.workspace_id]"
    )