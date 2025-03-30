from fastapi import APIRouter

from .supported_layers import api_supported_layers_router
from .upload_tg_packet import api_upload_tg_packet_router
from .messages import api_messages_router


SUBROUTERS = (
    api_supported_layers_router,
    api_upload_tg_packet_router,
    api_messages_router,
)


api_router = APIRouter(
    prefix = "/api"
)


for subrouter in SUBROUTERS:
    api_router.include_router(subrouter)


__all__ = [
    "api_router"
]
