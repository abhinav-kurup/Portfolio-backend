# app/services/chat/pipeline.py

from __future__ import annotations

from sqlite3 import Connection

from app.models.chat import ChatRequest, ChatResponse
from app.services.faq import find_faq_match
from app.services.guardrails import is_in_scope
from app.services.llm import generate_answer, condense_query
from app.services.prompts import NO_CONTEXT_RESPONSE, OUT_OF_SCOPE_RESPONSE
from app.services.retrievel_normalised import retrieve_context
from app.core.config import settings
# from app.services.knowledge_graph.retriever import (
#     extract_query_entities,
#     get_graph_context_string,
# )


def run_chat_pipeline(payload: ChatRequest, db: Connection) -> ChatResponse:
    original_query = payload.message.strip()
    history = payload.history
    
    search_query = condense_query(original_query, history)

    if not is_in_scope(search_query):
        return ChatResponse(**OUT_OF_SCOPE_RESPONSE)

    faq_match = find_faq_match(original_query, db)
    if faq_match is not None:
        return ChatResponse(
            response=faq_match["answer"],
            confidence=faq_match["score"],
            sources=[f"faq:{faq_match['id']}"]
        )

    chunks = retrieve_context(search_query, db, limit=settings.MAX_CHUNKS_RETRIEVED)

    if not chunks:
        return ChatResponse(**NO_CONTEXT_RESPONSE)

    import json
    context = "\n\n".join(
        f"[SOURCE: {chunk['title']}]\n[METADATA: {json.dumps(chunk['metadata'])}]\n{chunk['content']}"
        for chunk in chunks
    )

    # --- NEW: append graph facts to context ---
    # seed_entity_ids = extract_query_entities(original_query, db)
    # graph_facts = get_graph_context_string(seed_entity_ids, db)
    # if graph_facts:
    #     context = graph_facts + "\n\n" + context

    response = generate_answer(original_query, context, history)

    if not response.sources:
        response.sources = [f"doc:{chunk['id']}" for chunk in chunks]

    # if not response.follow_ups:
    #     response.follow_ups = [
    #         "What backend technologies does Abhinav use?",
    #         "What projects has Abhinav built?",
    #     ]

    return response