import uuid
import enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum, Integer, Boolean
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

class SprintStatus(str, enum.Enum):
    FUTURE = "Future"
    ACTIVE = "Active"
    COMPLETED = "Completed"

class TaskPriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class ProjectMember(Base):
    __tablename__ = "project_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    
    # FIXED: Added native_enum=False so values are seamlessly passed as plain text strings to PostgreSQL
    role = Column(Enum(ProjectRole, native_enum=False), nullable=False, default=ProjectRole.MEMBER)
    designation = Column(Enum(CorporateDesignation, native_enum=False), nullable=False, default=CorporateDesignation.NOT_ASSIGNED)
    
    employee_id = Column(String(50), nullable=False)  
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    employee = relationship("Employee", back_populates="project_memberships", primaryjoin="ProjectMember.user_id == Employee.id")
    project = relationship("Project", back_populates="members", primaryjoin="ProjectMember.project_id == Project.id")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)
    slug = Column(String(40), unique=True, nullable=False, index=True) 
    project_key = Column(String(20), unique=True, nullable=False, index=True) 
    ticket_counter = Column(Integer, default=0, nullable=False)
    created_on = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    board = relationship("Board", back_populates="project", uselist=False, cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Board(Base):
    __tablename__ = "boards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    name = Column(String(120), nullable=False) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="board")
    columns = relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan", order_by="BoardColumn.position")


class BoardColumn(Base):
    __tablename__ = "board_columns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(60), nullable=False) 
    position = Column(Integer, nullable=False) 
    wip_limit = Column(Integer, nullable=True) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    board = relationship("Board", back_populates="columns")
    tasks = relationship("Task", back_populates="column", cascade="all, delete-orphan")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False) 
    goal = Column(String(500), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(SprintStatus, native_enum=False), nullable=False, default=SprintStatus.FUTURE)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="sprints")
    tasks = relationship("Task", back_populates="sprint")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    column_id = Column(UUID(as_uuid=True), ForeignKey("board_columns.id", ondelete="CASCADE"), nullable=False)
    sprint_id = Column(UUID(as_uuid=True), ForeignKey("sprints.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)

    ticket_key = Column(String(30), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(2000), nullable=True)
    priority = Column(Enum(TaskPriority, native_enum=False), nullable=False, default=TaskPriority.MEDIUM)
    assignee_id = Column(String(50), nullable=True) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="tasks")
    column = relationship("BoardColumn", back_populates="tasks")
    sprint = relationship("Sprint", back_populates="tasks")
    subtasks = relationship("Task", cascade="all, delete-orphan")
