from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.dependencies import get_settings
from app.errors import install_handlers
from app.middleware import RateLimitMiddleware, RequestBoundary
from app.routers.analyses import router as analyses_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.services.rate_limit import build_limiter


@asynccontextmanager
async def lifespan(app):
    limiter = build_limiter(get_settings())
    app.state.rate_limiter = limiter
    try:
        async with httpx.AsyncClient(
            transport=httpx.AsyncHTTPTransport(retries=0), follow_redirects=False, trust_env=False
        ) as client:
            app.state.provider_client = client
            yield
    finally:
        await limiter.aclose()


app = FastAPI(title="JEV Resume Analyzer", debug=False, lifespan=lifespan)
install_handlers(app)
app.add_middleware(RequestBoundary)
# Outermost, so a limited caller never gets its body buffered.
app.add_middleware(RateLimitMiddleware)
app.include_router(health_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(analyses_router, prefix="/api/v1")
