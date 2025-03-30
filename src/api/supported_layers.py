from fastapi import APIRouter

from src import schemas
from src.global_variables import GlobalVariables


api_supported_layers_router = APIRouter()


supported_layers = sorted(GlobalVariables.layers_tlobjects.keys(), reverse=True)


@api_supported_layers_router.get(
    path = "/supported_layers",
    summary = "Get supported layers list"
)
async def api_supported_layers_handler() -> schemas.SupportedLayersResponse:
    return schemas.SupportedLayersResponse(
        supported_layers = supported_layers
    )
