from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
# from app.db.connection import init_db
from app.db.schema import create_schema
from app.db.seed import run_seed
from app.api import chat, contact
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info("Starting up...")
    create_schema()
    logger.info("Database initialized.")
    run_seed()
    logger.info("Seed complete.")
    yield
    # shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="Portfolio API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(chat.router,  prefix="/api",  tags=["chat"])
app.include_router(contact.router, prefix="/api", tags=["contact"])
# app.include_router(blogs.router, prefix="/api/v1/blogs", tags=["blogs"])
# app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "healthy",
        # "version": "1.0.0",
        # "environment": settings.APP_ENV
    }
