from fastapi import APIRouter, Depends, Request

from app.config import Settings
from app.dependencies import get_gateway, get_settings
from app.gateways.typesafe import TypeSafeGateway
from app.models.analyses import AnalysisReport
from app.services.analysis import analyse
from app.services.analysis_request import read_analysis

router = APIRouter()


@router.post("/analyses", response_model=AnalysisReport)
async def analyses(
    request: Request,
    gateway: TypeSafeGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
):
    """Score one CV. Accepts JSON text only, or multipart with an optional PDF.

    The multipart shape is the one the workspace uses: a part named `request` holds
    the JSON body and an optional part named `file` holds the PDF for the structure
    route. Both shapes return the same report.
    """
    body, upload = await read_analysis(request, settings)
    return await analyse(body, gateway, settings, request.state.request_id, upload)
