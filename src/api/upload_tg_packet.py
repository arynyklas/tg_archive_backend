from fastapi import APIRouter, Body
from pyrogram import raw, types
from pyrogram.parser.markdown import Markdown

import sqlalchemy as sa
import typing

from src import db, schemas, exceptions, utils
from src.api import _dependencies


api_upload_tg_packet_router = APIRouter()


@api_upload_tg_packet_router.post(
    path = "/upload_tg_packet",
    summary = "Upload Telegram raw packet",
    responses = exceptions.combine(
        # exceptions.ConcurrentRequestsError,
        exceptions.InvalidParametersError,
    )
)
# @_dependencies.block_concurrent_requests()
async def api_upload_tg_packet_handler(
    db_session: db.DBSession = _dependencies.get_db_session,
    request_obj: schemas.UploadTgPacketRequest = Body()
) -> schemas.OKResponse:
    try:
        auth_key, session_id, packet = request_obj.get_bytes()

    except ValueError as ex:
        raise exceptions.InvalidParametersError() from ex

    tl_message = utils.parse_tg_packet(packet, auth_key, session_id)

    if tl_message is None:
        raise exceptions.InvalidParametersError()

    if isinstance(tl_message.body, raw.types.rpc_result.RpcResult) and isinstance(tl_message.body.result, raw.types.updates_t.Updates):
        updates = tl_message.body.result.updates

        for update in updates:
            if isinstance(update, raw.types.update_new_channel_message.UpdateNewChannelMessage):
                message = update.message

                if isinstance(message, raw.types.message.Message):
                    if isinstance(message.peer_id, raw.types.peer_channel.PeerChannel) and isinstance(message.from_id, raw.types.peer_user.PeerUser):
                        tg_user_id = message.from_id.user_id
                        tg_chat_id = -1 * (message.peer_id.channel_id + 1_000_000_000_000)
                        tg_message_id = message.id
                        db_chat: db.Chat | None = None
                        db_user: db.User | None = None
                        chat_or_user_added = False

                        if not await db_session.scalar(
                            sa.select(sa.exists().where(
                                db.Chat.tg_chat_id == tg_chat_id
                            ))
                        ):
                            db_chat = db.Chat(
                                tg_chat_id = tg_chat_id
                            )

                            db_session.add(db_chat)

                            chat_or_user_added = True

                        if not await db_session.scalar(
                            sa.select(sa.exists().where(
                                db.User.tg_user_id == tg_user_id
                            ))
                        ):
                            db_user = db.User(
                                tg_user_id = tg_user_id
                            )

                            db_session.add(db_user)

                            chat_or_user_added = True

                        if not await db_session.scalar(
                            sa.select(sa.exists().where(
                                db.Message.tg_chat_id == tg_chat_id,
                                db.Message.tg_message_id == tg_message_id
                            ))
                        ):
                            if chat_or_user_added:
                                await db_session.flush()

                            entities = types.List(filter(lambda x: x is not None, [types.MessageEntity._parse(None, entity) for entity in (message.entities or [])]))  # type: ignore
                            md_text = typing.cast(str, Markdown.unparse(message.message, entities))  # type: ignore

                            db_session.add(db.Message(
                                tg_chat_id = tg_chat_id,
                                tg_user_id = tg_user_id,
                                tg_message_id = tg_message_id,
                                md_text = md_text,
                                sent_at = utils.get_datetime_utc_from_timestamp(message.date),
                                used_auth_key = auth_key,
                                used_session_id = session_id,
                                packet = packet,
                                chat = db_chat,
                                user = db_user
                            ))


    await db_session.commit()

    return schemas.OKResponse()
