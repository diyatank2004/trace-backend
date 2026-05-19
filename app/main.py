from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import connection engines
from app.database import engine, Base

# Important: Import models so SQLAlchemy binds metadata BEFORE creating tables
from app.auth.models import User
from app.projects.models import Project, ProjectMember

# Import modular routers
from app.auth.router import router as auth_router
from app.projects.router import router as project_router

# Synchronize schemas with PostgreSQL database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Trace Project Tracking Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(project_router)

@app.get("/")
def check_health():
    return {"status": "healthy", "database": "synchronized"}