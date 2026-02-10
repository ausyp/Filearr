from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from backend.db.database import get_db
from backend.db.models import ProcessedFile, RejectedFile
from sqlalchemy.orm import Session
from fastapi import Depends
import logging

# We'll implement cleanup module next
from backend.core.cleanup import run_manual_cleanup 

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")
logger = logging.getLogger(__name__)

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    recent_files = db.query(ProcessedFile).order_by(ProcessedFile.created_at.desc()).limit(50).all()
    rejected_files = db.query(RejectedFile).order_by(RejectedFile.created_at.desc()).limit(20).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "recent_files": recent_files,
        "rejected_files": rejected_files
    })

@router.get("/cleanup", response_class=HTMLResponse)
async def cleanup_page(request: Request):
    return templates.TemplateResponse("cleanup.html", {"request": request})

@router.post("/api/cleanup/start")
async def start_cleanup(background_tasks: BackgroundTasks, origin: str, dest: str, dry_run: bool = True):
    background_tasks.add_task(run_manual_cleanup, origin, dest, dry_run)
    return {"status": "Cleanup started", "mode": "dry_run" if dry_run else "live"}
