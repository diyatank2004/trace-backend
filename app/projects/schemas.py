from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List, Dict, Optional
from app.projects.models import ProjectRole, CorporateDesignation

class ProjectCreateRequest(BaseModel):
    project_name: str = Field(..., description="Name of the new project container")
    slug: str = Field(..., max_length=40)
    employee_id: str = Field(..., description="The Team Leader's Employee ID")

class ProjectResponse(BaseModel):
    id: UUID  # WS_id
    name: str
    slug: str
    project_key: str
    created_on: datetime

    class Config:
        from_attributes = True

class MemberJoinProjectRequest(BaseModel):
    project_key: str = Field(..., description="Unique code shared by the Team Leader")
    employee_id: str = Field(..., description="Employee ID of the member joining")
    designation: CorporateDesignation = Field(default=CorporateDesignation.DEVELOPER, description="Role assignment")

class ProjectSummaryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    project_key: str
    user_role_in_project: ProjectRole
    designation: CorporateDesignation

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
    designation_breakdown: Dict[str, int]  # e.g., {"Developer": 12, "Tester": 4...}
    recent_registrations: List[RecentUserLog]

    class Config:
        from_attributes = True