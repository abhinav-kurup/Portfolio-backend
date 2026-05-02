# app/services/chat/llm.py

from __future__ import annotations

from app.core.logging import setup_logging
from app.clients.llms import llm_client
from app.models.chat import ChatResponse
from app.services.prompts import SYSTEM_PROMPT

logger = setup_logging()


def generate_answer(query: str, context: str) -> ChatResponse:
    """
    Generate structured answer using:
    - primary: Groq
    - fallback: Gemini
    - validated structured output
    """
    try:
        response = llm_client.chat(
            system_promt=SYSTEM_PROMPT,
            user_prompt=f"Question:\n{query}\n\nContext:\n{context}",
        )

        return ChatResponse(
            response=response.response,
            confidence=response.confidence,
            sources=response.sources,
            # follow_ups=response.metadata.get("follow_ups", []),
            # in_scope=True,
        )

    except Exception as exc:
        logger.exception("LLM generation failed: %s", exc)

        return ChatResponse(
            response="I don't have enough verified context to answer that confidently.",
            confidence=0.0,
            sources=[],
            # follow_ups=[
            #     "What backend technologies does Abhinav use?",
            #     "What projects has Abhinav built?",
            # ],
            # in_scope=False,
        )