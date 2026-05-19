import secrets
import string
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.auth.models import Employee, GlobalRole
from app.projects.models import Project, ProjectMember, ProjectRole, CorporateDesignation
from app.projects.schemas import ProjectCreateRequest, ProjectResponse, MemberJoinProjectRequest, EmployeeDashboardOverview, ProjectSummaryResponse, AdminDashboardOverview, RecentUserLog
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/projects", tags=["Project Management"])

def generate_secure_project_key() -> str:
    chars = string.ascii_uppercase + string.digits
    return f"FLW-{''.join(secrets.choice(chars) for _ in range(6))}"

@router.post("/create", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_as_team_leader(data: ProjectCreateRequest, db: Session = Depends(get_db)):
    leader_user = db.query(Employee).filter(Employee.employee_id == data.employee_id).first()
    if not leader_user:
        raise HTTPException(
            status_code=404, 
            detail="Employee ID not found. Create a profile account before initiating a project."
        )

    if db.query(Project).filter(Project.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="project url slug is already in use.")

    new_project = Project(
        name=data.project_name,
        slug=data.slug,
        project_key=generate_secure_project_key()
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    leader_binding = ProjectMember(
        user_id=leader_user.id,
        project_id=new_project.id,
        employee_id=leader_user.employee_id,
        role=ProjectRole.TEAM_LEADER
    )
    db.add(leader_binding)
    db.commit()

    return new_project

@router.post("/join", status_code=status.HTTP_200_OK)
def join_project_as_member(data: MemberJoinProjectRequest, db: Session = Depends(get_db)):
    member_user = db.query(Employee).filter(Employee.employee_id == data.employee_id).first()
    if not member_user:
        raise HTTPException(status_code=404, detail="Employee ID record matching profile metrics not found.")

    project = db.query(Project).filter(Project.project_key == data.project_key).first()
    if not project:
        raise HTTPException(status_code=404, detail="Invalid project container access key sequence.")

    existing_membership = db.query(ProjectMember).filter(
        ProjectMember.user_id == member_user.id,
        ProjectMember.project_id == project.id
    ).first()
    if existing_membership:
        raise HTTPException(status_code=400, detail="This user has already joined this project partition.")

    new_membership = ProjectMember(
        user_id=member_user.id,
        project_id=project.id,
        employee_id=member_user.employee_id,
        role=ProjectRole.MEMBER,
        designation=data.designation
    )
    db.add(new_membership)
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully joined project dashboard: {project.name}",
        "project_id": str(project.id)
    }

# --- REQUIREMENT 2: TEAM LEADER DELETES project & CLEARS MEMBERS AUTOMATICALLY ---
@router.delete("/{project_id}/delete/{employee_id}", status_code=status.HTTP_200_OK)
def delete_project_as_team_leader(project_id: UUID, employee_id: str, db: Session = Depends(get_db)):
    # 1. Fetch user making the request
    requesting_user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not requesting_user:
        raise HTTPException(status_code=404, detail="Employee ID records do not exist.")

    # 2. Check project member linkage context
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == requesting_user.id
    ).first()

    # 3. Guard: Verify they belong here and hold the true 'Team Leader' privilege designation role
    if not membership or membership.role != ProjectRole.TEAM_LEADER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Only the designated Team Leader of this project can execute a full deletion."
        )

    # 4. Target project item row
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project data target not found.")

    # 5. Delete the project object. 
    # Because of our declarative primaryjoin relationship rules cascade configuration, 
    # SQLAlchemy and PostgreSQL automatically locate and wipe out all user membership lines 
    # connected to this project ID from project_members table cleanly!
    db.delete(project)
    db.commit()

    return {
        "status": "success",
        "message": f"project '{project.name}' successfully deleted. All team member access lines removed automatically."
    }

@router.get("/dashboard/{employee_id}", response_model=EmployeeDashboardOverview)
def get_employee_dashboard_overview(employee_id: str, db: Session = Depends(get_db)):
    """Fetches the unified workspace view containing all projects this user participates in."""
    # 1. Find the employee profile record
    user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Employee record not found.")

    # 2. Query all project membership intersections for this user
    memberships = db.query(ProjectMember).filter(ProjectMember.user_id == user.id).all()

    # 3. Formulate the dynamic response list
    project_list = []
    for m in memberships:
        # Fetch the associated project object data
        proj = db.query(Project).filter(Project.id == m.project_id).first()
        if proj:
            project_list.append({
                "id": proj.id,
                "name": proj.name,
                "slug": proj.slug,
                "project_key": proj.project_key,
                "user_role_in_project": m.role  # Dynamics: Varies per item inline
            })

    return {
        "employee_id": user.employee_id,
        "full_name": user.full_name,
        "email": user.email,
        "active_projects": project_list
    }

# --- SECURED ADMIN DASHBOARD CORE GETTER ---
@router.get("/admin/overview-stats", response_model=AdminDashboardOverview)
def get_admin_dashboard_metrics(
    db: Session = Depends(get_db),
    current_admin: Employee = Depends(get_current_user)  # Extract & verify bearer token
):
    """Aggregates corporate global metrics to populate the Admin high-level supervision console."""
    # 1. Security Guard: Enforce that the user is explicitly an Admin
    if current_admin.global_role != GlobalRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Only system administrators can pull administrative analytics."
        )

    # 2. Compute overall counts
    total_projects_count = db.query(Project).count()
    
    # We count only users who are corporate employees (filtering out other admin profiles)
    total_employees_count = db.query(Employee).filter(Employee.global_role == GlobalRole.USER).count()

    # 3. Compute dynamic breakdown of professional corporate designations inside project groups
    # Group by the ProjectMember designation enum and aggregate counts
    designation_query = db.query(
        ProjectMember.designation, 
        func.count(ProjectMember.user_id)
    ).group_by(ProjectMember.designation).all()

    # Translate database results safely into a clean dictionary map for the UI graphs
    breakdown_map = {}
    for enum_val, count in designation_query:
        if enum_val:
            breakdown_map[enum_val.value] = count

    # 4. Fetch the 5 most recently onboarded employees to populate a 'Recent Activity' stream feed
    recent_users = db.query(Employee).filter(
        Employee.global_role == GlobalRole.USER
    ).order_by(Employee.created_at.desc()).limit(5).all()

    recent_logs_list = []
    for u in recent_users:
        recent_logs_list.append({
            "employee_id": u.employee_id or "N/A",
            "full_name": u.full_name,
            "email": u.email or "N/A",
            "created_at": u.created_at
        })

    # 5. Return unified analytics response payload package
    return {
        "total_projects": total_projects_count,
        "total_employees": total_employees_count,
        "designation_breakdown": breakdown_map,
        "recent_registrations": recent_logs_list
    }