from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.chat import router as chat_router
from app.api.files import router as files_router
from app.api.health import router as health_router
from app.api.pages import router as pages_router
from app.api.projects import router as projects_router
from app.api.settings import router as settings_router
from app.api.themes import router as themes_router

router = APIRouter()
router.include_router(health_router)
router.include_router(projects_router)
router.include_router(pages_router)
router.include_router(settings_router)
router.include_router(themes_router)
router.include_router(files_router)
router.include_router(chat_router)
router.include_router(agent_router)
