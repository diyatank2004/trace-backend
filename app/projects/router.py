import secrets
import string
from uuid import UUID
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.config import settings  # For JWT expiration settings metrics
from app.auth.utils import create_access_token  # To issue tokens over the wire
from app.auth.models import Employee, GlobalRole
from app.auth.dependencies import get_current_user
from app.projects.models import (
    Project, ProjectMember, ProjectRole, CorporateDesignation, 
    Board, BoardColumn, Sprint, SprintStatus, Task
)
from app.projects.schemas import (
    ProjectCreateRequest, ProjectResponse, AddTeamMemberRequest,
    EmployeeDashboardOverview, AdminDashboardOverview, BoardDetailResponse,
    SprintCreateRequest, SprintResponse, SprintUpdateRequest,
    TaskCreateRequest, TaskResponse, ChangeLeadRequest,
    ProjectAccessVerificationRequest, TokenVerificationResponse
)

router = APIRouter(prefix="/projects", tags=["Project Spaces & Agile Core"])

def generate_secure_project_key() -> str:
    """Generates unique base short alphanumeric identifier codes (e.g., TRACE)"""
    chars = string.ascii_uppercase
    return "".join(secrets.choice(chars) for _ in range(5))


# --- 1. CORE WORKSPACE FLOWS ---

@router.post("/create", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_as_team_leader(data: ProjectCreateRequest, db: Session = Depends(get_db)):
    """Creates a new project container space and automatically seeds the 9 custom status lanes."""
    leader_user = db.query(Employee).filter(Employee.employee_id == data.employee_id).first()
    if not leader_user:
        raise HTTPException(status_code=404, detail="Employee ID not found. Register an account first.")

    if db.query(Project).filter(Project.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="Project URL slug identifier is already in use.")

    new_project = Project(
        name=data.project_name,
        slug=data.slug,
        project_key=generate_secure_project_key().upper(),
        ticket_counter=0
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    # Bind creator immediately as Team Leader
    leader_binding = ProjectMember(
        user_id=leader_user.id,
        project_id=new_project.id,
        employee_id=leader_user.employee_id,
        role=ProjectRole.TEAM_LEADER,
        designation=CorporateDesignation.PRODUCT_MANAGER
    )
    db.add(leader_binding)

    # Build connected board space container
    default_board = Board(project_id=new_project.id, name=f"{new_project.name} Visual Space")
    db.add(default_board)
    db.commit()
    
    # 9 Strict custom workflow layout columns
    default_columns = [
        "To Do", "In Progress", "Testing", "Development Complete",
        "Peer Review", "QA Move", "UAT Move", "Production Deploy", "Done"
    ]
    for index, column_name in enumerate(default_columns):
        seeded_column = BoardColumn(board_id=default_board.id, name=column_name, position=index)
        db.add(seeded_column)
    
    db.commit()
    return new_project


@router.post("/add-member", status_code=status.HTTP_201_CREATED)
def team_leader_add_member_by_id(
    data: AddTeamMemberRequest, 
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Guards workspace allocation: Only the verified Team Leader can add corporate profiles by ID."""
    # 1. Look up the sender's role inside this specific project based on their secure token ID
    authorization_check = db.query(ProjectMember).filter(
        ProjectMember.project_id == data.project_id,
        ProjectMember.user_id == current_user.id
    ).first()

    # 2. Security Guard: If they are not the project's Team Leader, block them instantly
    if not authorization_check or authorization_check.role != ProjectRole.TEAM_LEADER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Enforcement: Access Denied. Only the verified Team Leader can add members."
        )

    # 3. Check if the target teammate exists in the corporate directory
    worker = db.query(Employee).filter(Employee.employee_id == data.employee_id).first()
    if not worker:
        raise HTTPException(
            status_code=404, 
            detail=f"Allocation Failure: Target Employee ID '{data.employee_id}' not found."
        )

    # 4. Guard against duplicates
    existing_binding = db.query(ProjectMember).filter(
        ProjectMember.project_id == data.project_id,
        ProjectMember.user_id == worker.id
    ).first()
    
    if existing_binding:
        raise HTTPException(
            status_code=400, 
            detail=f"Conflict: Employee '{worker.full_name}' is already assigned to this project."
        )

    # 5. Cleanly instantiate the member assignment row
    new_team_member = ProjectMember(
        user_id=worker.id,
        project_id=data.project_id,
        employee_id=worker.employee_id,
        role=ProjectRole.MEMBER,
        designation=data.designation
    )
    
    db.add(new_team_member)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Successfully allocated '{worker.full_name}' to the project team."
    }


# --- 2. PASSWORD-LESS SESSION INITIALIZATION GATEWAYS ---

@router.post("/verify-access", response_model=TokenVerificationResponse, status_code=status.HTTP_200_OK)
def verify_workspace_session_access(data: ProjectAccessVerificationRequest, db: Session = Depends(get_db)):
    """Authenticates team profiles without password layers via employee_id + assigned project_key."""
    project = db.query(Project).filter(Project.project_key == data.project_key.upper()).first()
    if not project:
        raise HTTPException(status_code=404, detail="Access Denied: The specified Project Key does not exist.")

    employee = db.query(Employee).filter(Employee.employee_id == data.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Access Denied: Employee ID not found in system directory.")

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project.id,
        ProjectMember.employee_id == data.employee_id
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Employee '{employee.full_name}' is not assigned to Project '{project.name}'."
        )

    # Issue secure cryptographic token session tracking metrics
    session_time_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    issued_token = create_access_token(
        data={
            "sub": str(employee.id),
            "project_id": str(project.id),
            "project_role": membership.role.value
        },
        expires_delta=session_time_delta
    )

    return {
        "status": "authenticated",
        "access_token": issued_token,
        "token_type": "bearer",
        "user_meta": {
            "full_name": employee.full_name,
            "project_id": project.id,
            "project_name": project.name,
            "assigned_role": membership.role.value,
            "designation": membership.designation.value
        }
    }


# --- 3. AGILE CORE PARTS (SPRINTS & TASKS) ---

@router.post("/sprints/create", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
def create_new_sprint_backlog(data: SprintCreateRequest, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Target agile project context not found.")
    new_sprint = Sprint(
        project_id=data.project_id, 
        name=data.name, 
        goal=data.goal, 
        start_date=data.start_date, 
        end_date=data.end_date, 
        status=SprintStatus.FUTURE
    )
    db.add(new_sprint)
    db.commit()
    db.refresh(new_sprint)
    return new_sprint


@router.post("/tasks/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_agile_task(data: TaskCreateRequest, db: Session = Depends(get_db)):
    """Generates an issue, automates naming suffix keys, and registers it in the baseline lane (Position 0)."""
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Parent Agile project data entity context not found.")

    todo_lane = db.query(BoardColumn).join(Board).filter(
        Board.project_id == data.project_id,
        BoardColumn.position == 0
    ).first()
    if not todo_lane:
        raise HTTPException(status_code=404, detail="Default workflow columns layout missing from project grid.")

    project.ticket_counter += 1
    generated_code = f"{project.project_key}-{project.ticket_counter}"

    new_task = Task(
        project_id=data.project_id,
        column_id=todo_lane.id,
        sprint_id=data.sprint_id,
        parent_id=data.parent_id,
        ticket_key=generated_code,
        title=data.title,
        description=data.description,
        priority=data.priority,
        assignee_id=data.assignee_id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/{project_id}/board", response_model=BoardDetailResponse)
def get_project_visual_board(project_id: UUID, db: Session = Depends(get_db)):
    board = db.query(Board).options(
        joinedload(Board.columns).joinedload(BoardColumn.tasks)
    ).filter(Board.project_id == project_id).first()
    
    if not board:
        raise HTTPException(
            status_code=404, 
            detail="Agile board framework infrastructure not initialized for this project."
        )
    return board


@router.patch("/tasks/{task_id}/move-lane/{column_id}", response_model=TaskResponse)
def transfer_task_visual_status_lane(task_id: UUID, column_id: UUID, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Target task ticket not found.")

    target_lane = db.query(BoardColumn).filter(BoardColumn.id == column_id).first()
    if not target_lane:
        raise HTTPException(status_code=404, detail="Target column lane does not exist.")

    target_board = db.query(Board).filter(Board.id == target_lane.board_id).first()
    if not target_board or target_board.project_id != task.project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Security Block: Column lane context mismatch. Cannot transfer tasks across separate project scopes."
        )

    task.column_id = target_lane.id
    db.commit()
    db.refresh(task)
    return task


@router.get("/{project_id}/sprints", response_model=List[SprintResponse])
def list_all_project_sprints(project_id: UUID, db: Session = Depends(get_db)):
    """Returns sprints cleanly sorted with Active timelines prioritized over future planning metrics."""
    return db.query(Sprint).filter(Sprint.project_id == project_id).order_by(
        Sprint.status == SprintStatus.ACTIVE,
        Sprint.created_at.desc()
    ).all()


@router.patch("/sprints/{sprint_id}/update", response_model=SprintResponse)
def update_or_start_sprint(sprint_id: UUID, data: SprintUpdateRequest, db: Session = Depends(get_db)):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Target sprint cycle record not found.")
    
    if data.status == SprintStatus.ACTIVE:
        active_sprint_check = db.query(Sprint).filter(
            Sprint.project_id == sprint.project_id, 
            Sprint.status == SprintStatus.ACTIVE, 
            Sprint.id != sprint.id
        ).first()
        if active_sprint_check:
            raise HTTPException(status_code=400, detail=f"Cannot start sprint. '{active_sprint_check.name}' is currently active.")
            
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sprint, key, value)
    db.commit()
    db.refresh(sprint)
    return sprint


# --- 4. DASHBOARD PANELS & METRICS ---

@router.get("/dashboard/{employee_id}", response_model=EmployeeDashboardOverview)
def get_employee_dashboard_overview(employee_id: str, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee record not found.")
    memberships = db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all()
    project_list = []
    for m in memberships:
        proj = db.query(Project).filter(Project.id == m.project_id).first()
        if proj:
            project_list.append({
                "id": proj.id, "name": proj.name, "slug": proj.slug, "project_key": proj.project_key, 
                "user_role_in_project": m.role, "user_designation": m.designation
            })
    return {"employee_id": user.employee_id, "full_name": user.full_name, "email": user.email, "active_projects": project_list}


@router.get("/admin/overview-stats", response_model=AdminDashboardOverview)
def get_admin_dashboard_metrics(db: Session = Depends(get_db), current_admin: Employee = Depends(get_current_user)):
    if current_admin.global_role != GlobalRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied. Only system administrators can pull administrative analytics.")
    total_projects_count = db.query(Project).count()
    total_employees_count = db.query(Employee).filter(Employee.global_role == GlobalRole.USER).count()
    
    designation_query = db.query(ProjectMember.designation, func.count(ProjectMember.user_id)).group_by(ProjectMember.designation).all()
    breakdown_map = {d.value: 0 for d in CorporateDesignation}
    for enum_val, count in designation_query:
        if enum_val: breakdown_map[enum_val.value] = count
        
    recent_users = db.query(Employee).filter(Employee.global_role == GlobalRole.USER).order_by(Employee.created_at.desc()).limit(5).all()
    recent_logs_list = []
    for u in recent_users: 
        recent_logs_list.append({"employee_id": u.employee_id or "N/A", "full_name": u.full_name, "email": u.email or "N/A", "created_at": u.created_at})
        
    return {"total_projects": total_projects_count, "total_employees": total_employees_count, "designation_breakdown": breakdown_map, "recent_registrations": recent_logs_list}


# --- 5. SYSTEM CONTROL OVERRIDES (DELETIONS & TRANSFERS) ---

@router.delete("/{project_id}/delete/{employee_id}", status_code=status.HTTP_200_OK)
def delete_project_as_team_leader(project_id: UUID, employee_id: str, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee record profile metrics not found.")
    membership = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id).first()
    if not membership or membership.role != ProjectRole.TEAM_LEADER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied. Only the designated Team Leader can delete this project container.")
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Target project space data not found.")
    db.delete(project)
    db.commit()
    return {"status": "success", "message": f"Project '{project.name}' successfully deleted."}


@router.patch("/admin/change-lead", status_code=status.HTTP_200_OK)
def admin_transfer_project_leadership(
    data: ChangeLeadRequest, 
    db: Session = Depends(get_db),
    current_admin: Employee = Depends(get_current_user) # 🔒 FIXED: Extracts and verifies identity from bearer tokens
):
    
    # 1. SECURITY LOCK: Double check they are an Admin and not a standard user spoofing requests
    if current_admin.global_role != GlobalRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Only global platform administrators can reassign project ownership."
        )

    # 2. Locate the old leader member row entry
    old_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == data.project_id,
        ProjectMember.employee_id == data.old_leader_employee_id
    ).first()
    
    # 3. Locate the employee who will step up as the new Team Leader
    new_leader_employee = db.query(Employee).filter(Employee.employee_id == data.new_leader_employee_id).first()
    if not new_leader_employee:
        raise HTTPException(status_code=404, detail="The employee designated as the new leader does not exist.")

    # 4. Check if the new leader is already a member of the project
    new_member = db.query(ProjectMember).filter(
        ProjectMember.project_id == data.project_id,
        ProjectMember.user_id == new_leader_employee.id
    ).first()

    # Demote old leader to a regular member status cleanly
    if old_member:
        old_member.role = ProjectRole.MEMBER

    # Promote the new worker to Team Leader mapping configurations
    if new_member:
        new_member.role = ProjectRole.TEAM_LEADER
        new_member.designation = CorporateDesignation.PRODUCT_MANAGER
    else:
        # If they weren't in the project yet, create a fresh membership row as Team Leader
        new_member = ProjectMember(
            user_id=new_leader_employee.id,
            project_id=data.project_id,
            employee_id=new_leader_employee.employee_id,
            role=ProjectRole.TEAM_LEADER,
            designation=CorporateDesignation.PRODUCT_MANAGER
        )
        db.add(new_member)

    db.commit()
    return {"status": "success", "message": f"Leadership successfully transferred to Employee ID {data.new_leader_employee_id}"}

@router.delete("/admin/delete/{project_id}", status_code=status.HTTP_200_OK)
def admin_force_delete_project(project_id: UUID, db: Session = Depends(get_db), current_admin: Employee = Depends(get_current_user)):
    if current_admin.global_role != GlobalRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied. Only system administrators can execute global deletions.")

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Target project record space not found in system storage.")

    db.delete(project)
    db.commit()
    return {"status": "success", "message": f"Administrative Action Complete: Project '{project.name}' successfully deleted."}