# app/services/chat/llm.py

from __future__ import annotations

from app.core.logging import setup_logging
from app.clients.llms import llm_client
from app.models.chat import ChatResponse
from app.services.prompts import SYSTEM_PROMPT

logger = setup_logging()


def condense_query(query: str, history: list[Any] = None) -> str:
    """
    Rephrase the query based on history to make it standalone for retrieval.
    """
    if not history:
        return query
    
    from app.services.prompts import CONDENSE_PROMPT
    
    standalone_query = llm_client.raw_chat(
        system_prompt=CONDENSE_PROMPT,
        user_prompt=f"Follow-up question: {query}",
        history=history
    )
    
    logger.info("Condensed query: %s", standalone_query)
    return standalone_query 


def generate_answer(query: str, context: str, history: list[Any] = None) -> ChatResponse:
    """
    Generate structured answer using history and context.
    """
    try:
        from app.services.prompts import build_chat_prompt
        response = llm_client.chat(
            system_promt=SYSTEM_PROMPT,
            user_prompt=build_chat_prompt(query, context),
            history=history
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