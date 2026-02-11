from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router
from backend.core.watcher import start_watchers
import logging
from loguru import logger
import sys

from backend.api.settings import router as settings_router

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("/data/filearr.log", rotation="10 MB", level="INFO")

app = FastAPI(title="Filearr", description="Intelligent Movie Ingestion & Cleanup Engine")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation Error for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Failed", "detail": exc.errors()}
    )

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Include API routes
app.include_router(router)
app.include_router(settings_router)

@app.on_event("startup")
async def startup():
    logger.info("Starting Filearr backend...")
    from backend.db.database import init_db
    init_db()
    start_watchers()
    logger.info("Filearr started successfully.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
