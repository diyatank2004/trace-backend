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

class CorporateDesignation(str, enum.Enum):
    DEVELOPER = "Developer"
    TESTER = "Tester"
    DEVOPS = "DevOps Engineer"
    DESIGNER = "UI/UX Designer"
    PRODUCT_MANAGER = "Product Manager"
    NOT_ASSIGNED = "Not Assigned"

class ProjectMember(Base):
    __tablename__ = "project_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    
    role = Column(Enum(ProjectRole), nullable=False)
    designation = Column(Enum(CorporateDesignation), nullable=False)
    employee_id = Column(String(50), ForeignKey("employees.employee_id", ondelete="CASCADE"), nullable=False)  
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Explicit mapping definitions targeting column variables
    employee = relationship("Employee", back_populates="project_memberships", primaryjoin="ProjectMember.user_id == Employee.id")
    project = relationship("Project", back_populates="members", primaryjoin="ProjectMember.project_id == Project.id")

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