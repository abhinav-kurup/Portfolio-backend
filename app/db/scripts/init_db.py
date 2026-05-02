import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.schema import create_schema

if __name__ == "__main__":
    print("Initializing database...")
    create_schema()
    print("Done — all tables created.")