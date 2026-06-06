from __future__ import annotations

from sqlite3 import Connection
from app.core.logging import setup_logging
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

logger = setup_logging()

class QueryEntities(BaseModel):
    entities: list[str] = Field(description="List of key entities extracted from the query. Focus on names of people, projects, skills, technologies, and core concepts.")

def extract_query_entities(query: str, db: Connection) -> list[int]:
    """
    LLM-based NER: use an LLM to extract entities from the query, 
    then match them against the kg_entities table.
    """
    provider = settings.PRIMARY_LLM_PROVIDER
    model = settings.PRIMARY_LLM_MODEL

    if provider == "groq":
        llm = ChatGroq(
            model=model,
            max_tokens=250,
            temperature=0.0,
            api_key=settings.GROK_API_KEY
        )
    elif provider == "google":
        llm = ChatGoogleGenerativeAI(
            model=model,
            max_tokens=200,
            temperature=0.0,
            api_key=settings.GEMINI_API_KEY
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
        
    structured_llm = llm.with_structured_output(QueryEntities)
    prompt = f"Extract the key entities from the following query to use for a knowledge graph search:\n\nQuery: {query}"
    
    extracted_names = []
    try:
        response = structured_llm.invoke(prompt)
        extracted_names = [e.lower() for e in response.entities]
        logger.info(f"  [KG] LLM extracted entities: {extracted_names}")
    except Exception as e:
        logger.error(f"Failed to extract entities using LLM: {e}")
        return []

    if not extracted_names:
        return []

    rows = db.execute("SELECT id, name FROM kg_entities").fetchall()

    matched_ids = []
    for row in rows:
        db_name = row["name"].lower()
        # Strict match but allowing for simple plurals
        if (db_name in extracted_names or 
            db_name + "s" in extracted_names or 
            db_name.rstrip("s") in extracted_names):
            
            if row["id"] not in matched_ids:
                matched_ids.append(row["id"])
                logger.info(f"  [KG] Matched DB entity: {row['name']} (id={row['id']})")

    return matched_ids


def get_related_doc_ids(
    entity_ids: list[int],
    db: Connection,
    hops: int = 1,
) -> set[int]:
    """
    Walk the graph up to `hops` levels from seed entities.
    Returns the set of doc_ids connected to discovered entities.
    """
    if not entity_ids:
        return set()

    visited_entities: set[int] = set(entity_ids)
    frontier: set[int] = set(entity_ids)

    for _ in range(hops):
        if not frontier:
            break

        placeholders = ",".join("?" * len(frontier))
        rows = db.execute(
            f"""
            SELECT DISTINCT
                CASE WHEN subject_id IN ({placeholders}) THEN object_id
                     ELSE subject_id END AS neighbor_id
            FROM kg_relations
            WHERE subject_id IN ({placeholders})
               OR object_id  IN ({placeholders})
            """,
            [*frontier, *frontier, *frontier],
        ).fetchall()

        next_frontier = set()
        for row in rows:
            nid = row["neighbor_id"]
            if nid not in visited_entities:
                visited_entities.add(nid)
                next_frontier.add(nid)

        frontier = next_frontier

    # Get all doc_ids linked to discovered entities
    if not visited_entities:
        return set()

    placeholders = ",".join("?" * len(visited_entities))
    doc_rows = db.execute(
        f"SELECT DISTINCT doc_id FROM kg_entities WHERE id IN ({placeholders})",
        list(visited_entities),
    ).fetchall()

    doc_ids = {row["doc_id"] for row in doc_rows if row["doc_id"]}
    logger.info(f"[KG] Graph traversal found {len(doc_ids)} related docs from {len(entity_ids)} seed entities")
    return doc_ids


def get_graph_context_string(entity_ids: list[int], db: Connection) -> str:
    """
    Format discovered triples as a readable string to inject into the LLM prompt.
    """
    if not entity_ids:
        return ""

    placeholders = ",".join("?" * len(entity_ids))
    rows = db.execute(
        f"""
        SELECT
            es.name AS subject,
            r.predicate,
            eo.name AS object
        FROM kg_relations r
        JOIN kg_entities es ON es.id = r.subject_id
        JOIN kg_entities eo ON eo.id = r.object_id
        WHERE r.subject_id IN ({placeholders})
           OR r.object_id  IN ({placeholders})
        LIMIT 30
        """,
        [*entity_ids, *entity_ids],
    ).fetchall()

    if not rows:
        return ""

    lines = [f"- {row['subject']} → {row['predicate']} → {row['object']}" for row in rows]
    return "Knowledge Graph Facts:\n" + "\n".join(lines)
