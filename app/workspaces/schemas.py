from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class WorkspaceCreateRequest(BaseModel):
    workspace_name: str = Field(..., description="Name of the new project container")
    slug: str = Field(..., max_length=40)
    employee_id: str = Field(..., description="The Team Leader's Employee ID")

class WorkspaceResponse(BaseModel):
    id: UUID  # WS_id
    name: str
    slug: str
    workspace_key: str
    created_on: datetime

    class Config:
        from_attributes = True

class MemberJoinRequest(BaseModel):
    workspace_key: str
    employee_id: str