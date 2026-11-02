from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.rag import router as rag_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.agent import router as agent_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.ml import router as ml_router
from app.api.v1.aegisops import router as aegisops_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(documents_router)
api_router.include_router(rag_router)
api_router.include_router(assistant_router)
api_router.include_router(agent_router)
api_router.include_router(tickets_router)
api_router.include_router(ml_router)
api_router.include_router(aegisops_router)
