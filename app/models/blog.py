from pydantic import Field
from typing import Any

from app.models.common import BaseSchema


class BlogPost(BaseSchema):
    title: str = Field(..., description="Blog post title")
    content: str = Field(..., description="Blog post content")
    source_path: str = Field(..., description="Blog post source path")
    cover_image: str | None = Field(default=None, description="Blog post cover image")
    published: bool = Field(default=False, description="Blog post published status")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Blog post metadata")
