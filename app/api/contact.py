import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.contact import ContactSubmission
from app.core.logging import setup_logging

logger = setup_logging()

router = APIRouter(
    prefix="/contact",
    tags=["contact"],
)

CONTACT_FILE = "data/contact_submissions.json"

def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

@router.post("/", summary="Submit contact form")
def submit_contact(submission: ContactSubmission):
    ensure_data_dir()
    
    # Add timestamp if not provided
    if not submission.timestamp:
        submission.timestamp = datetime.now()
    
    submissions = []
    if os.path.exists(CONTACT_FILE):
        try:
            with open(CONTACT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    submissions = json.loads(content)
        except Exception as e:
            logger.error(f"Error reading contact file: {e}")
            # If corrupted, start fresh or handle accordingly
            submissions = []

    # Append new submission
    # Convert datetime to string for JSON serialization
    submission_dict = submission.model_dump()
    submission_dict["timestamp"] = submission_dict["timestamp"].isoformat()
    
    submissions.append(submission_dict)
    
    try:
        with open(CONTACT_FILE, "w", encoding="utf-8") as f:
            json.dump(submissions, f, indent=4)
        return {"status": "success", "message": "Message sent successfully"}
    except Exception as e:
        logger.error(f"Error writing contact file: {e}")
        raise HTTPException(status_code=500, detail="Could not save message")

@router.get("/", response_model=List[dict], summary="Retrieve contact submissions")
def get_submissions():
    if not os.path.exists(CONTACT_FILE):
        return []
    
    try:
        with open(CONTACT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
            return []
    except Exception as e:
        logger.error(f"Error reading contact file: {e}")
        raise HTTPException(status_code=500, detail="Could not read messages")
