from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class ContactSubmission(BaseModel):
    name: str
    email: EmailStr
    message: str
    timestamp: Optional[datetime] = None
