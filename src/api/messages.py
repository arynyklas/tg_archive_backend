from fastapi import APIRouter, Query
from fastapi.exceptions import RequestValidationError

import sqlalchemy as sa
import typing

from src import db, schemas, exceptions
from src.api import _dependencies


api_messages_router = APIRouter()


PAGINATION_LIMIT = 100


@api_messages_router.get(
    path = "/messages",
    summary = "Get messages",
    responses = exceptions.combine(
        # exceptions.ConcurrentRequestsError,
        # exceptions.InvalidParametersError,
    )
)
# @_dependencies.block_concurrent_requests()
async def api_get_messages_handler(
    db_session: db.DBSession = _dependencies.get_db_session,
    tg_chat_id: int | None = Query(
        default = None,
        description = "Telegram chat ID"
    ),
    tg_user_id: int | None = Query(
        default = None,
        description = "Telegram user ID"
    ),
    tg_message_ids: list[int] | None = Query(
        default = None,
        description = "Telegram message IDs",
        examples = [
            [1, 2, 3]
        ]
    ),
    tg_message_ids_start: int | None = Query(
        default = None,
        description = "Telegram message ID to start from"
    ),
    tg_message_ids_end: int | None = Query(
        default = None,
        description = "Telegram message ID to end with"
    ),
    offset: int = Query(
        default = 0,
        ge = 0,
        description = "Offset for pagination"
    ),
    limit: int = Query(
        default = PAGINATION_LIMIT,
        ge = 1,
        le = PAGINATION_LIMIT,
        description = "Limit for pagination"
    )
) -> schemas.ListMessages:
    db_query_filters: set[sa.ColumnElement[typing.Any]] = set()

    if tg_chat_id:
        db_query_filters.add(db.Message.tg_chat_id == tg_chat_id)
    if tg_user_id:
        db_query_filters.add(db.Message.tg_user_id == tg_user_id)

    if tg_message_ids and (tg_message_ids_start or tg_message_ids_end):
        raise RequestValidationError(
            errors = [
                {
                    "loc": ["query", "tg_message_ids", "tg_message_ids_start", "tg_message_ids_end"],
                    "msg": "tg_message_ids and tg_message_ids_start/tg_message_ids_end cannot be used together",
                    "type": "value_error"
                }
            ]
        )

    elif (tg_message_ids_start is None) != (tg_message_ids_end is None):
        raise RequestValidationError(
            errors = [
                {
                    "loc": ["query", "tg_message_ids_start", "tg_message_ids_end"],
                    "msg": "tg_message_ids_start and tg_message_ids_end must be used together",
                    "type": "value_error"
                }
            ]
        )

    if tg_message_ids:
        db_query_filters.add(db.Message.tg_message_id.in_(tg_message_ids))

    elif tg_message_ids_start and tg_message_ids_end:
        if tg_message_ids_start > tg_message_ids_end:
            tg_message_ids_start, tg_message_ids_end = tg_message_ids_end, tg_message_ids_start

        db_query_filters.add(db.Message.tg_message_id.between(tg_message_ids_start, tg_message_ids_end))

    db_messages = (await db_session.execute(
        sa.select(db.Message)
        .where(*db_query_filters)
        .order_by(db.Message.sent_at.desc())
        .offset(offset)
        # .limit(limit + 1)
        .limit(limit)
    )).scalars().all()

    # has_next = len(db_messages) > limit

    # if has_next:
    #     db_messages.pop()

    return schemas.ListMessages(
        messages = [
            schemas.Message(
                id = db_message.id,
                tg_chat_id = db_message.tg_chat_id,
                tg_user_id = db_message.tg_user_id,
                tg_message_id = db_message.tg_message_id,
                reply_to_tg_message_id = db_message.reply_to_tg_message_id,
                md_text = db_message.md_text,
                sent_at = db_message.sent_at,
                used_auth_key = db_message.used_auth_key.hex(),
                used_session_id = db_message.used_session_id.hex(),
                packet = db_message.packet.hex(),
                inserted_at = db_message.inserted_at
            )
            for db_message in db_messages
        ],
        # has_next = has_next
    )
