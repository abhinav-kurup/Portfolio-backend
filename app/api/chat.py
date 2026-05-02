# app/api/chat.py

from fastapi import APIRouter, Depends
from sqlite3 import Connection

from app.db.connection import get_db
from app.core.logging import setup_logging
from app.models.chat import ChatRequest, ChatResponse
from app.services.pipeline import run_chat_pipeline

logger = setup_logging()


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post(
    "/",
    response_model=ChatResponse,
    summary="Portfolio chatbot",
    description="Ask questions about Abhinav's skills, projects, backend experience, and technical background.",
)
def chat(
    payload: ChatRequest,
    db: Connection = Depends(get_db),
) -> ChatResponse:
    logger.info("Chat request received", extra={"payload": payload})
    return run_chat_pipeline(payload, db)