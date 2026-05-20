import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import get_settings
from api.routes import router
from api.websocket import ws_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "flood_command_starting",
        simulation_mode=settings.simulation_mode,
        gemini_configured=bool(settings.gemini_api_key),
        firebase_configured=bool(settings.firebase_project_id),
    )
    yield
    logger.info("flood_command_shutdown")


app = FastAPI(
    title="Karachi Flood Command Center",
    description="Multi-agent AI system for urban flood monitoring and emergency response",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, tags=["REST"])
app.include_router(ws_router, tags=["WebSocket"])

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def root():
    return {
        "system": "Karachi Flood Command Center",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
    }
