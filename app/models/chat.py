from pydantic import BaseModel,ConfigDict,Field
from typing import TypedDict, Any

from app.models.common import BaseSchema



class Message(BaseModel):
    role: str = Field(..., description="Role of the sender (user/assistant)")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseSchema):
    message: str = Field(..., description="Current user message")
    conversation_id: str | None = Field(default=None)
    history: list[Message] = Field(default_factory=list, description="Recent conversation history")


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
    metadata: dict[str, Any]
    score: float