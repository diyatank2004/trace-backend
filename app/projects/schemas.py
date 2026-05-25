from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from typing import List, Dict, Optional
from datetime import datetime
from app.projects.models import ProjectRole, CorporateDesignation, SprintStatus, TaskPriority

# --- 1. BASIC BASELINE STRUCTURES ---
class ProjectCreateRequest(BaseModel):
    project_name: str = Field(..., min_length=2, max_length=120)
    slug: str = Field(..., min_length=2, max_length=40)
    employee_id: str = Field(..., description="Employee ID of creating Team Leader")

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    project_key: str

    class Config:
        from_attributes = True

class AddTeamMemberRequest(BaseModel):
    project_id: UUID = Field(..., description="The context workspace UUID")
    employee_id: str = Field(..., description="The unique identity string of the worker to assign")
    designation: CorporateDesignation = Field(default=CorporateDesignation.DEVELOPER)

# --- 2. ADMIN & USER DASHBOARDS ---
class ProjectSummaryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    project_key: str
    user_role_in_project: ProjectRole
    user_designation: CorporateDesignation

    class Config:
        from_attributes = True

class EmployeeDashboardOverview(BaseModel):
    employee_id: str
    full_name: str
    email: str
    active_projects: List[ProjectSummaryResponse]

    class Config:
        from_attributes = True

class RecentUserLog(BaseModel):
    employee_id: str
    full_name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdminDashboardOverview(BaseModel):
    total_projects: int
    total_employees: int
    designation_breakdown: Dict[str, int]
    recent_registrations: List[RecentUserLog]

    class Config:
        from_attributes = True

# --- 3. TASK SCHEMAS ---
class TaskCreateRequest(BaseModel):
    project_id: UUID
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    sprint_id: Optional[UUID] = None  
    parent_id: Optional[UUID] = None  
    assignee_id: Optional[str] = None 

class TaskResponse(BaseModel):
    id: UUID
    ticket_key: str
    project_id: UUID
    column_id: UUID
    sprint_id: Optional[UUID]
    parent_id: Optional[UUID]
    title: str
    description: Optional[str]
    priority: TaskPriority
    assignee_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# --- 4. BOARD COLUMNS & SPRINTS ---
class ColumnResponse(BaseModel):
    id: UUID
    name: str
    position: int
    wip_limit: Optional[int]
    tasks: List[TaskResponse] = []

    class Config:
        from_attributes = True

class BoardDetailResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    columns: List[ColumnResponse]

    class Config:
        from_attributes = True

class SprintCreateRequest(BaseModel):
    project_id: UUID
    name: str = Field(..., min_length=2, max_length=120)
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SprintUpdateRequest(BaseModel):
    name: Optional[str] = None
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[SprintStatus] = None

class SprintResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    goal: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: SprintStatus

    class Config:
        from_attributes = True

# --- 5. ADMINISTRATIVE OVERRIDES INPUT VALIDATIONS ---
class ChangeLeadRequest(BaseModel):
    project_id: UUID
    old_leader_employee_id: str
    new_leader_employee_id: str

class ProjectAccessVerificationRequest(BaseModel):
    employee_id: str = Field(..., description="The employee ID typing into the interface gate")
    project_key: str = Field(..., description="The short project code text prefix constraint (e.g., TEJ, TRACE)")

# --- 6. AUTHENTICATION & TOKEN SESSION RESPONSES ---
class UserWorkspaceMeta(BaseModel):
    full_name: str
    project_id: UUID
    project_name: str
    assigned_role: str
    designation: str

class TokenVerificationResponse(BaseModel):
    status: str
    access_token: str
    token_type: str
    user_meta: UserWorkspaceMeta