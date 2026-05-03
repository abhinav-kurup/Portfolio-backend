import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connection import get_connection
from app.services.pipeline import run_chat_pipeline
from app.models.chat import ChatRequest

def test():
    conn = get_connection()
    try:
        req = ChatRequest(message="What is E-Beat and who built it?")
        res = run_chat_pipeline(req, conn)
        print("\n\n=== RESPONSE ===")
        print(res.response)
        print("Sources:", res.sources)
    finally:
        conn.close()

if __name__ == "__main__":
    test()
