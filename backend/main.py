from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router
from backend.core.watcher import start_watchers
import logging
from loguru import logger
import sys

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

app = FastAPI(title="MediaMind", description="Intelligent Movie Ingestion & Cleanup Engine")

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Include API routes
app.include_router(router)

@app.on_event("startup")
async def startup():
    logger.info("Starting MediaMind backend...")
    from backend.db.database import init_db
    init_db()
    start_watchers()
    logger.info("MediaMind started successfully.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
