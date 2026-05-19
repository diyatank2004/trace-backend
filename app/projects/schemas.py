from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List
from app.projects.models import ProjectRole

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

class MemberJoinRequest(BaseModel):
    project_key: str
    employee_id: str

class ProjectSummaryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    project_key: str
    user_role_in_project: ProjectRole

    class Config:
        from_attributes = True

class EmployeeDashboardOverview(BaseModel):
    employee_id: str
    full_name: str
    email: str
    active_projects: List[ProjectSummaryResponse]

    class Config:
        from_attributes = True