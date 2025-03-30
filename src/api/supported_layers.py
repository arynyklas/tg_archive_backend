from fastapi import APIRouter
from pyrogram.raw.all import layer as supported_layer

from src import schemas


api_supported_layers_router = APIRouter()


@api_supported_layers_router.get(
    path = "/supported_layers",
    summary = "Get supported layers list"
)
async def api_supported_layers_handler() -> schemas.SupportedLayersResponse:
    return schemas.SupportedLayersResponse(
        supported_layers = [supported_layer]
    )
