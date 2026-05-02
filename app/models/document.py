# app/models/document.py

from __future__ import annotations

from typing import TypedDict

from pydantic import Field

from app.models.common import BaseSchema


# ----------------------------
# Admin / Ingest Models
# ----------------------------

class DocumentCreate(BaseSchema):
    doc_type: str = Field(..., examples=["skill", "project", "experience"])
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    source_path: str | None = None
    metadata: dict = Field(default_factory=dict)


class DocumentResponse(BaseSchema):
    id: int
    doc_type: str
    title: str
    content: str
    source_path: str | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: str
    updated_at: str


# ----------------------------
# Internal Retrieval Contracts
# ----------------------------

class RetrievedDocument(TypedDict):
    id: int
    title: str
    content: str
    score: float