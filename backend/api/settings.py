from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.core.config_service import config_service
import logging

router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")
logger = logging.getLogger(__name__)

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    config = config_service.get_all_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": config
    })

@router.post("/api/settings/save")
async def save_settings(
    request: Request,
):
    form = await request.form()
    
    # Save known settings
    keys = ["TMDB_API_KEY", "INPUT_DIR", "OUTPUT_DIR"]
    
    for key in keys:
        if key in form:
            config_service.set_setting(key, form[key])
            
    # Redirect back to settings with success message (simplified)
    return RedirectResponse(url="/settings?saved=true", status_code=303)
