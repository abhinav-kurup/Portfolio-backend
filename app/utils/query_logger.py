import json
import os
from datetime import datetime

def log_interaction(query: str, reply: str, file_path: str = "data/chat_logs.json"):
    """
    Appends a user query and the corresponding reply to a JSON file.
    Creates the file and directory if they don't exist.
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    data = []
    
    # Load existing data if file exists
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if not isinstance(data, list):
                        data = [data] # Convert to list if it's a single object somehow
        except (json.JSONDecodeError, IOError):
            # Start fresh if file is corrupted or empty
            pass

    # Append new interaction
    interaction = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "reply": reply
    }
    data.append(interaction)

    # Write back to the file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
