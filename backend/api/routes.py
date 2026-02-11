from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from backend.db.database import get_db
from backend.db.models import ProcessedFile, RejectedFile, ErrorLog, CleanupLog, WatcherLog
from sqlalchemy.orm import Session
from fastapi import Depends
from loguru import logger

# We'll implement cleanup module next
from backend.core.cleanup import run_manual_cleanup
from backend.core.directory_service import directory_service
from backend.core.ignore_service import ignore_service 

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    recent_files = db.query(ProcessedFile).order_by(ProcessedFile.created_at.desc()).limit(50).all()
    rejected_files = db.query(RejectedFile).order_by(RejectedFile.created_at.desc()).limit(20).all()
    error_logs = db.query(ErrorLog).order_by(ErrorLog.timestamp.desc()).limit(20).all()
    cleanup_logs = db.query(CleanupLog).order_by(CleanupLog.timestamp.desc()).limit(30).all()
    from backend.core.watcher import watcher_manager
    watch_path = watcher_manager.watched_path or "Not Active"
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "recent_files": recent_files,
        "rejected_files": rejected_files,
        "error_logs": error_logs,
        "cleanup_logs": cleanup_logs,
        "watch_path": watch_path
    })

@router.get("/cleanup", response_class=HTMLResponse)
async def cleanup_page(request: Request):
    from backend.core.config_service import config_service
    config = config_service.get_all_settings()
    return templates.TemplateResponse("cleanup.html", {
        "request": request,
        "config": config
    })

from pydantic import BaseModel

class CleanupRequest(BaseModel):
    origin_dir: str
    malayalam_dest: str
    english_dest: str
    dry_run: bool = True

@router.post("/api/cleanup/start")
async def start_cleanup(request: CleanupRequest, background_tasks: BackgroundTasks):
    from backend.core.cleanup import run_manual_cleanup, cleanup_manager
    import os
    
    # Relaxed root: allow anything under /media (our primary volume)
    ALLOWED_ROOTS = ["/media"]
    
    # Safety guard: ensure paths start with allowed roots
    if not any(request.origin_dir.startswith(root) for root in ALLOWED_ROOTS):
        logger.error(f"Invalid origin path: {request.origin_dir}. Must start with {' or '.join(ALLOWED_ROOTS)}")
        return {"error": f"Invalid origin path. Must start with {' or '.join(ALLOWED_ROOTS)}"}
    
    if not any(request.malayalam_dest.startswith(root) for root in ALLOWED_ROOTS):
        logger.error(f"Invalid Malayalam destination path: {request.malayalam_dest}. Must start with {' or '.join(ALLOWED_ROOTS)}")
        return {"error": f"Invalid Malayalam destination path. Must start with {' or '.join(ALLOWED_ROOTS)}"}
    
    if not any(request.english_dest.startswith(root) for root in ALLOWED_ROOTS):
        logger.error(f"Invalid English destination path: {request.english_dest}. Must start with {' or '.join(ALLOWED_ROOTS)}")
        return {"error": f"Invalid English destination path. Must start with {' or '.join(ALLOWED_ROOTS)}"}
    
    # Check if a cleanup is already running
    if cleanup_manager.is_running:
        return {"status": "error", "message": "Cleanup already in progress"}

    # All validations passed, start cleanup
    background_tasks.add_task(
        run_manual_cleanup,
        request.origin_dir,
        request.malayalam_dest,
        request.english_dest,
        request.dry_run
    )
    
    return {
        "status": "success", 
        "message": "Cleanup started in background",
        "mode": "dry_run" if request.dry_run else "live"
    }

@router.post("/api/cleanup/stop")
async def stop_cleanup():
    from backend.core.cleanup import cleanup_manager
    cleanup_manager.stop()
    return {"status": "success", "message": "Stop signal sent"}

@router.get("/api/cleanup/status")
async def get_cleanup_status():
    from backend.core.cleanup import cleanup_manager
    return {
        "is_running": cleanup_manager.is_running,
        "should_stop": cleanup_manager.should_stop,
        "current_file": cleanup_manager.current_file
    }

@router.get("/api/logs/errors")
async def get_error_logs(limit: int = 50, db: Session = Depends(get_db)):
    """
    Retrieve recent error logs.
    """
    error_logs = db.query(ErrorLog).order_by(ErrorLog.timestamp.desc()).limit(limit).all()
    
    return [{
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "level": log.level,
        "source": log.source,
        "message": log.message,
        "traceback": log.traceback
    } for log in error_logs]

@router.get("/api/logs/cleanup")
async def get_cleanup_logs(limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve recent cleanup operation logs.
    """
    cleanup_logs = db.query(CleanupLog).order_by(CleanupLog.timestamp.desc()).limit(limit).all()
    
    return [{
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "operation_type": log.operation_type,
        "file_path": log.file_path,
        "destination": log.destination,
        "status": log.status,
        "details": log.details
    } for log in cleanup_logs]

@router.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Monitoring dashboard page"""
    return templates.TemplateResponse("monitoring.html", {"request": request})

@router.get("/api/monitoring/stats")
async def get_monitoring_stats(db: Session = Depends(get_db)):
    """Get system statistics for monitoring"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from backend.core.watcher import watcher_manager
    
    today = datetime.utcnow().date()
    
    # Count files processed today
    processed_today = db.query(func.count(WatcherLog.id)).filter(
        WatcherLog.action == "processed",
        func.date(WatcherLog.timestamp) == today
    ).scalar() or 0
    
    # Count errors today
    errors_today = db.query(func.count(WatcherLog.id)).filter(
        WatcherLog.action == "failed",
        func.date(WatcherLog.timestamp) == today
    ).scalar() or 0
    
    # Count ignored today
    ignored_today = db.query(func.count(WatcherLog.id)).filter(
        WatcherLog.action == "ignored",
        func.date(WatcherLog.timestamp) == today
    ).scalar() or 0
    
    # Get last activity
    last_activity = db.query(WatcherLog).order_by(WatcherLog.timestamp.desc()).first()
    last_activity_time = last_activity.timestamp.isoformat() if last_activity else None
    
    status = watcher_manager.get_status()
    
    return {
        "processed_today": processed_today,
        "errors_today": errors_today,
        "ignored_today": ignored_today,
        "last_activity": last_activity_time,
        "watcher_status": "running" if status["is_running"] else "stopped",
        "watched_path": status["watched_path"]
    }

@router.post("/api/monitoring/watcher/stop")
async def stop_watcher():
    from backend.core.watcher import watcher_manager
    watcher_manager.stop()
    return {"status": "success", "message": "Watcher stopped"}

@router.post("/api/monitoring/watcher/start")
async def start_watcher():
    from backend.core.watcher import watcher_manager
    watcher_manager.start()
    return {"status": "success", "message": "Watcher started"}

@router.post("/api/monitoring/watcher/restart")
async def restart_watcher():
    from backend.core.watcher import watcher_manager
    watcher_manager.restart()
    return {"status": "success", "message": "Watcher restarted"}

@router.get("/api/monitoring/activity")
async def get_monitoring_activity(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent watcher activity"""
    activity = db.query(WatcherLog).order_by(WatcherLog.timestamp.desc()).limit(limit).all()
    
    return [{
        "id": log.id,
        "timestamp": log.timestamp.isoformat(),
        "event_type": log.event_type,
        "file_path": log.file_path,
        "action": log.action,
        "reason": log.reason
    } for log in activity]

@router.get("/api/ignore/patterns")
async def get_ignore_patterns():
    """Get all ignore patterns"""
    patterns = ignore_service.get_ignore_patterns()
    return {"patterns": patterns}

@router.post("/api/ignore/add")
async def add_ignore_pattern(pattern: str):
    """Add a new ignore pattern"""
    if not pattern or not pattern.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Pattern cannot be empty"}
        )
    
    success = ignore_service.add_pattern(pattern.strip())
    if success:
        return {"status": "success", "pattern": pattern.strip()}
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to add pattern"}
        )

@router.delete("/api/ignore/remove")
async def remove_ignore_pattern(pattern: str):
    """Remove an ignore pattern"""
    success = ignore_service.remove_pattern(pattern)
    if success:
        return {"status": "success", "pattern": pattern}
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to remove pattern"}
        )

@router.get("/api/ignore/files")
async def get_ignored_files():
    """Get all specifically ignored files"""
    files = ignore_service.get_ignored_files()
    return {"files": files}

@router.post("/api/ignore/file/add")
async def add_ignored_file(file_path: str, reason: str = None):
    """Add a specific file to ignore list"""
    if not file_path or not file_path.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "File path cannot be empty"}
        )
    
    success = ignore_service.add_ignored_file(file_path.strip(), reason)
    if success:
        return {"status": "success", "file_path": file_path.strip()}
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to add file to ignore list"}
        )

@router.delete("/api/ignore/file/remove")
async def remove_ignored_file(file_path: str):
    """Remove a specific file from ignore list"""
    success = ignore_service.remove_ignored_file(file_path)
    if success:
        return {"status": "success", "file_path": file_path}
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to remove file from ignore list"}
        )
@router.get("/api/debug/logs")
async def get_system_logs():
    """Diagnostic endpoint to read the log file"""
    import os
    log_path = "/data/filearr.log"
    if not os.path.exists(log_path):
        return {"error": "Log file not found"}
    with open(log_path, "r") as f:
        # Get last 100 lines
        lines = f.readlines()
        return {"logs": lines[-100:]}

@router.get("/api/debug/ls")
async def debug_list_files(path: str = "/media"):
    """Diagnostic endpoint to see what the container sees"""
    import os
    if not os.path.exists(path):
        return {"error": f"Path {path} not found"}
    
    structure = []
    try:
        for root, dirs, files in os.walk(path):
            # Limit depth for safety or just show everything if it's a small path
            rel_path = os.path.relpath(root, path)
            structure.append({
                "path": rel_path,
                "dirs": dirs,
                "files": files
            })
            if len(structure) > 100: # Safety break
                break
        return {"structure": structure}
    except Exception as e:
        return {"error": str(e)}
