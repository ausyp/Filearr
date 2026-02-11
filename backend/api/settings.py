from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from backend.core.config_service import config_service
from backend.core.directory_service import directory_service
import logging
import os

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")
logger = logging.getLogger(__name__)

from backend.core.watcher import watcher_manager
from backend.core.tmdb import test_tmdb_api

@router.get("/api/settings/test-tmdb")
async def verify_tmdb_key(api_key: str = Query(...)):
    success, message = test_tmdb_api(api_key)
    if success:
        return {"success": True, "message": message}
    return JSONResponse(status_code=400, content={"success": False, "message": message})

@router.post("/api/settings/save")
async def save_settings(
    request: Request,
):
    form = await request.form()
    
    # Save known settings
    keys = [
        "TMDB_API_KEY", 
        "INPUT_DIR", "OUTPUT_DIR", 
        "MOVIES_DIR", "MALAYALAM_DIR", "REJECTED_DIR", "TRASH_DIR"
    ]
    
    old_input_dir = config_service.get_setting("INPUT_DIR")
    
    for key in keys:
        if key in form:
            config_service.set_setting(key, form[key])
            
    # If input dir changed, restart watcher
    new_input_dir = config_service.get_setting("INPUT_DIR")
    if old_input_dir != new_input_dir:
        logger.info(f"Input directory changed from {old_input_dir} to {new_input_dir}. Restarting watcher.")
        watcher_manager.restart()
            
    # Redirect back to settings with success message (simplified)
    return RedirectResponse(url="/settings?saved=true", status_code=303)

@router.get("/api/browse")
async def browse_filesystem(path: str = Query(default="/media")):
    try:
        data = directory_service.list_directories(path)
        if "error" in data:
            return JSONResponse(status_code=400, content=data)
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error browsing directory {path}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
