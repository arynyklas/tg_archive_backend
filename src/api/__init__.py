from fastapi import APIRouter

from .upload_tg_packet import api_upload_tg_packet_router
from .messages import api_messages_router


SUBROUTERS = (
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
