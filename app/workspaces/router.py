import secrets
import string
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.models import User
from app.workspaces.models import Workspace, WorkspaceMember, WorkspaceRole
from app.workspaces.schemas import WorkspaceCreateRequest, WorkspaceResponse, MemberJoinRequest

router = APIRouter(prefix="/workspaces", tags=["Workspace Management"])

def generate_secure_workspace_key() -> str:
    chars = string.ascii_uppercase + string.digits
    return f"FLW-{''.join(secrets.choice(chars) for _ in range(6))}"

@router.post("/create", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_as_team_leader(data: WorkspaceCreateRequest, db: Session = Depends(get_db)):
    leader_user = db.query(User).filter(User.employee_id == data.employee_id).first()
    if not leader_user:
        raise HTTPException(
            status_code=404, 
            detail="Employee ID not found. Create a profile account before initiating a workspace."
        )

    if db.query(Workspace).filter(Workspace.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="Workspace url slug is already in use.")

    new_workspace = Workspace(
        name=data.workspace_name,
        slug=data.slug,
        workspace_key=generate_secure_workspace_key()
    )
    db.add(new_workspace)
    db.commit()
    db.refresh(new_workspace)

    leader_binding = WorkspaceMember(
        user_id=leader_user.id,
        workspace_id=new_workspace.id,
        employee_id=leader_user.employee_id,
        role=WorkspaceRole.TEAM_LEADER
    )
    db.add(leader_binding)
    db.commit()

    return new_workspace

@router.post("/join", status_code=status.HTTP_200_OK)
def join_workspace_as_member(data: MemberJoinRequest, db: Session = Depends(get_db)):
    member_user = db.query(User).filter(User.employee_id == data.employee_id).first()
    if not member_user:
        raise HTTPException(status_code=404, detail="Employee ID record matching profile metrics not found.")

    workspace = db.query(Workspace).filter(Workspace.workspace_key == data.workspace_key).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Invalid workspace container access key sequence.")

    existing_membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == member_user.id,
        WorkspaceMember.workspace_id == workspace.id
    ).first()
    if existing_membership:
        raise HTTPException(status_code=400, detail="This user has already joined this workspace partition.")

    new_membership = WorkspaceMember(
        user_id=member_user.id,
        workspace_id=workspace.id,
        employee_id=member_user.employee_id,
        role=WorkspaceRole.MEMBER
    )
    db.add(new_membership)
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully joined workspace dashboard: {workspace.name}",
        "workspace_id": str(workspace.id)
    }

# --- REQUIREMENT 2: TEAM LEADER DELETES WORKSPACE & CLEARS MEMBERS AUTOMATICALLY ---
@router.delete("/{workspace_id}/delete/{employee_id}", status_code=status.HTTP_200_OK)
def delete_workspace_as_team_leader(workspace_id: UUID, employee_id: str, db: Session = Depends(get_db)):
    # 1. Fetch user making the request
    requesting_user = db.query(User).filter(User.employee_id == employee_id).first()
    if not requesting_user:
        raise HTTPException(status_code=404, detail="Employee ID records do not exist.")

    # 2. Check workspace member linkage context
    membership = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == requesting_user.id
    ).first()

    # 3. Guard: Verify they belong here and hold the true 'Team Leader' privilege designation role
    if not membership or membership.role != WorkspaceRole.TEAM_LEADER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Only the designated Team Leader of this workspace can execute a full deletion."
        )

    # 4. Target workspace item row
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace data target not found.")

    # 5. Delete the workspace object. 
    # Because of our declarative primaryjoin relationship rules cascade configuration, 
    # SQLAlchemy and PostgreSQL automatically locate and wipe out all user membership lines 
    # connected to this workspace ID from workspace_members table cleanly!
    db.delete(workspace)
    db.commit()

    return {
        "status": "success",
        "message": f"Workspace '{workspace.name}' successfully deleted. All team member access lines removed automatically."
    }