import uuid
import enum
from sqlalchemy import Column, String, DateTime, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class GlobalRole(str, enum.Enum):
    ADMIN = "Admin"
    USER = "User"

class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    global_role = Column(Enum(GlobalRole), nullable=False, default=GlobalRole.USER)
    
    # Core Manual Registration Fields
    employee_id = Column(String(50), unique=True, nullable=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(254), unique=True, nullable=True, index=True)
    phone_number = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True) # Global professional title
    skills = Column(String(500), nullable=True) # Comma-separated list (e.g. "Python, React")
    
    # Platform Tracking Status Flags
    availability_status = Column(String(50), nullable=False, default="Available") # e.g. "Available", "In a Meeting", "On Leave"
    is_active = Column(Boolean, default=True)
    
    # Admin Unique Login Access Credentials
    username = Column(String(50), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship to the project crossover table mapping cleanly
    project_memberships = relationship(
        "ProjectMember", 
        back_populates="employee", 
        cascade="all, delete-orphan",
        primaryjoin="Employee.id == ProjectMember.user_id"
    )