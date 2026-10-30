import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.errors import install_handlers
from app.middleware import RequestBoundary
from app.routers.analyses import router as analyses_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router

DEFAULT_ALLOWED_ORIGINS = "http://127.0.0.1:5273,http://localhost:5273"


def allowed_origins(raw: str | None = None) -> list[str]:
    """Parse a comma separated origin list. A trailing slash never matches a browser Origin."""
    value = DEFAULT_ALLOWED_ORIGINS if raw is None else raw
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(
        transport=httpx.AsyncHTTPTransport(retries=0), follow_redirects=False, trust_env=False
    ) as client:
        app.state.provider_client = client
        yield


app = FastAPI(title="JEV Resume Analyzer", debug=False, lifespan=lifespan)
install_handlers(app)
app.add_middleware(RequestBoundary)
# Added last so it runs first and answers preflights before the body boundary.
# Only the configured web origins, GET and POST, plain content-type, no credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(os.getenv("ALLOWED_ORIGINS")),
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
    allow_credentials=False,
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(analyses_router, prefix="/api/v1")
