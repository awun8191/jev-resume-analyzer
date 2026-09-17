from fastapi import APIRouter, Depends, Request

from app.config import Settings
from app.dependencies import get_gateway, get_settings
from app.gateways.typesafe import TypeSafeGateway
from app.models.analyses import AnalysisReport, AnalysisRequest
from app.services.analysis import analyse

router = APIRouter()


@router.post("/analyses", response_model=AnalysisReport)
async def analyses(
    body: AnalysisRequest,
    request: Request,
    gateway: TypeSafeGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
):
    return await analyse(body, gateway, settings, request.state.request_id)
