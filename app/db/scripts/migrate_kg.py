import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.schema import create_schema

if __name__ == "__main__":
    create_schema()
    print("Migration complete. KG tables added.")
