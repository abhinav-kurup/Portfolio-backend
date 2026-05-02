from pydantic import BaseModel,ConfigDict,Field
from typing import TypedDict, Any

from app.models.common import BaseSchema



class ChatRequest(BaseSchema):
    message : str = Field(...,description="User's message")
    conversation_id: str | None = Field(default=None,description="Conversation ID")


class ChatResponse(BaseSchema):
    response: str = Field(...,description="LLM response")
    confidence: float = Field(...,ge=0,le=1,description="Confidence score")
    metadata :dict[str,Any] = Field(default_factory=dict,description="Metadata")
    sources : list[str] = Field(default_factory=list,description="Sources")


class FAQMatch(TypedDict):
    id: int
    question: str
    answer: str
    score: float


class RetrievedChunk(TypedDict):
    id: int
    title: str
    content: str
    score: float