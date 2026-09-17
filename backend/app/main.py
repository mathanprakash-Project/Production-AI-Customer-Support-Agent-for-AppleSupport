"""
FastAPI Application Entrypoint and Factory.
Mounts API v1 routes, middleware, CORS, and lifecycle event handlers.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.evaluation import router as eval_router
from app.api.v1.health import router as health_router
from app.api.v1.inference import router as inference_router
from app.api.v1.intents import router as intents_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.analytics import router as analytics_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db.init_db import init_db

setup_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown handler."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    try:
        await init_db()
        logger.info("Database schemas and seed data verified.")
    except Exception as e:
        logger.error(f"Database initialization warning: {e}")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Production-oriented AI Customer Support Agent with pgvector RAG, Ollama, and LLM evaluation.",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and timing middleware
    app.add_middleware(RequestContextMiddleware)

    # Register API v1 routes
    prefix = settings.API_V1_PREFIX
    app.include_router(health_router, prefix=prefix)
    app.include_router(auth_router, prefix=prefix)
    app.include_router(tickets_router, prefix=prefix)
    app.include_router(inference_router, prefix=prefix)
    app.include_router(intents_router, prefix=prefix)
    app.include_router(eval_router, prefix=prefix)
    app.include_router(knowledge_router, prefix=prefix)
    app.include_router(analytics_router, prefix=prefix)

    # Root route
    @app.get("/")
    async def root():
        return {
            "name": settings.APP_NAME,
            "status": "online",
            "docs_url": "/docs",
            "api_v1": settings.API_V1_PREFIX,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

