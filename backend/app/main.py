from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.errors import install_handlers
from app.middleware import RequestBoundary
from app.routers.analyses import router as analyses_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router


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
app.include_router(health_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(analyses_router, prefix="/api/v1")
