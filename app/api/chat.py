# app/api/chat.py
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlite3 import Connection
from app.utils.query_logger import log_interaction

from app.db.connection import get_db
from app.core.logging import setup_logging
from app.models.chat import ChatRequest, ChatResponse
from app.services.pipeline import run_chat_pipeline
from app.api.deps import get_admin_key

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
    print("PAYLOAD",payload)
    response = run_chat_pipeline(payload, db)
    log_interaction(payload, response)
    return response

@router.get(
    "/logs",
    summary="Retrieve chat logs",
    description="Returns the chat logs stored in the JSON file. Requires admin API key.",
)
def get_chat_logs(admin_key: str = Depends(get_admin_key)):
    file_path = "data/chat_logs.json"
    if not os.path.exists(file_path):
        return {"logs": []}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
                return {"logs": data}
            return {"logs": []}
    except Exception as e:
        logger.error(f"Error reading chat logs: {e}")
        raise HTTPException(status_code=500, detail="Could not read chat logs")
