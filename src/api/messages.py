from fastapi import APIRouter, Depends

import sqlalchemy as sa
import typing

from src import db, schemas, exceptions
from src.api import _dependencies


api_messages_router = APIRouter()


@api_messages_router.get(
    path = "/messages",
    summary = "Get messages",
    responses = exceptions.combine(
        # exceptions.ConcurrentRequestsError,
        exceptions.InvalidParametersError,
    )
)
# @_dependencies.block_concurrent_requests()
async def api_get_messages_handler(
    db_session: db.DBSession = _dependencies.get_db_session,
    request_obj: schemas.GetMessagesRequest = Depends()
) -> schemas.ListMessages:
    db_query_filters: set[sa.ColumnElement[typing.Any]] = set()

    if request_obj:
        if request_obj.chat_id:
            db_query_filters.add(db.Message.tg_chat_id == request_obj.chat_id)
        if request_obj.user_id:
            db_query_filters.add(db.Message.tg_user_id == request_obj.user_id)

    return schemas.ListMessages(
        messages = [
            schemas.Message(
                id = db_message.id,
                tg_chat_id = db_message.tg_chat_id,
                tg_user_id = db_message.tg_user_id,
                tg_message_id = db_message.tg_message_id,
                md_text = db_message.md_text,
                sent_at = db_message.sent_at,
                used_auth_key = db_message.used_auth_key.hex(),
                used_session_id = db_message.used_session_id.hex(),
                packet = db_message.packet.hex(),
                inserted_at = db_message.inserted_at
            )
            for db_message in (await db_session.execute(
                sa.select(db.Message)
                .where(*db_query_filters)
                .order_by(db.Message.sent_at.desc())
            )).scalars().all()
        ]
    )
