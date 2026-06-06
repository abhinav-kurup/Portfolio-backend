from __future__ import annotations

import json
import re
from sqlite3 import Connection
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging()

class Entity(BaseModel):
    name: str = Field(description="Name of the entity, exact string from text.")
    type: str = Field(description="Type of entity: PERSON, SKILL, PROJECT, TECHNOLOGY, COMPANY, or OTHER")

class Relation(BaseModel):
    subject: str = Field(description="Subject entity name")
    predicate: str = Field(description="Relationship verb (lowercase): uses, built, works_at, knows, led, etc.")
    object: str = Field(description="Object entity name")

class GraphExtraction(BaseModel):
    entities: list[Entity]
    relations: list[Relation]

EXTRACTION_PROMPT = """
Extract entities and relationships from the text below.

Rules:
- Entity names must be exact strings from the text
- Predicates should be lowercase verbs: "uses", "built", "works_at", "knows", "led", "developed_by", "is_a"
- If the text describes a project, explicitly create TWO relationships: [Project Name] -> "developed_by" -> "Abhinav Kurup", and [Project Name] -> "is_a" -> "Project"
- Only extract high-confidence triples

Text:
{text}
"""

def extract_graph(text: str) -> dict:
    """Call LLM to extract entities + relations from a document chunk."""
    provider = settings.PRIMARY_LLM_PROVIDER
    model = settings.PRIMARY_LLM_MODEL

    if provider == "groq":
        llm = ChatGroq(
            model=model,
            max_tokens=1000,
            temperature=0.0,
            api_key=settings.GROK_API_KEY
        )
    elif provider == "google":
        llm = ChatGoogleGenerativeAI(
            model=model,
            max_tokens=1000,
            temperature=0.0,
            api_key=settings.GEMINI_API_KEY
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
        
    structured_llm = llm.with_structured_output(GraphExtraction)
    prompt = EXTRACTION_PROMPT.format(text=text[:3000])
    
    try:
        response = structured_llm.invoke(prompt)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Failed to extract graph using structured output: {e}")
        return {"entities": [], "relations": []}


def index_document_graph(doc_id: int, content: str, db: Connection) -> None:
    """
    Extract and store graph triples for a document.
    Call this from your existing document ingest pipeline.
    """
    try:
        graph = extract_graph(content)
    except Exception as e:
        logger.warning(f"Graph extraction failed for doc {doc_id}: {e}")
        return

    entity_name_to_id: dict[str, int] = {}

    # Upsert entities
    for ent in graph.get("entities", []):
        name = ent["name"].strip()
        etype = ent.get("type", "OTHER")
        if not name:
            continue

        cursor = db.execute(
            """
            INSERT INTO kg_entities (name, type, doc_id)
            VALUES (?, ?, ?)
            ON CONFLICT(name, doc_id) DO UPDATE SET type = excluded.type
            RETURNING id
            """,
            [name, etype, doc_id],
        )
        row = cursor.fetchone()
        if row:
            entity_name_to_id[name] = row["id"]

    # Insert relations
    for rel in graph.get("relations", []):
        subj_id = entity_name_to_id.get(rel["subject"])
        obj_id  = entity_name_to_id.get(rel["object"])
        if not subj_id or not obj_id:
            continue  # skip if entity wasn't found

        db.execute(
            """
            INSERT OR IGNORE INTO kg_relations (subject_id, predicate, object_id, doc_id)
            VALUES (?, ?, ?, ?)
            """,
            [subj_id, rel["predicate"], obj_id, doc_id],
        )

    db.commit()
    logger.info(
        f"Indexed graph for doc {doc_id}: "
        f"{len(entity_name_to_id)} entities, {len(graph.get('relations', []))} relations"
    )
