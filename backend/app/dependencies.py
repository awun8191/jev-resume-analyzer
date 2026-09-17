from functools import lru_cache

from fastapi import Depends, Request

from app.config import Settings
from app.gateways.typesafe import TypeSafeGateway


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_gateway(request: Request, settings: Settings = Depends(get_settings)) -> TypeSafeGateway:
    return TypeSafeGateway(request.app.state.provider_client, settings)
