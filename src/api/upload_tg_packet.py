from fastapi import APIRouter, Body
from fastapi.exceptions import RequestValidationError
from telethon.tl import types as tl_types
from telethon.tl.tlobject import TLObject
from telethon.tl.core import TLMessage
from functools import partial

import sqlalchemy as sa
import typing

from src import db, schemas, exceptions
from src.api import _dependencies
from src.global_variables import GlobalVariables
from src.tg_packet_parser import parse_tg_packet, BinaryReader, tgread_object
from src.markdown_utils import unparse_markdown


api_upload_tg_packet_router = APIRouter()


def _is_tlobject_same_by_constructor_id(tlobject: TLObject, name: str, needed_layers_tlobject_constructor_ids: dict[str, int]) -> bool:
    return tlobject and typing.cast(int, tlobject.CONSTRUCTOR_ID) == needed_layers_tlobject_constructor_ids[name]


dummy_cte = sa.select(sa.literal(1).label("dummy")).cte("dummy")


@api_upload_tg_packet_router.post(
    path = "/upload_tg_packet",
    summary = "Upload Telegram raw packet",
    responses = exceptions.combine(
        # exceptions.InvalidLayerError,
    )
)
async def api_upload_tg_packet_handler(
    db_session: db.DBSession = _dependencies.get_db_session,
    request_obj: schemas.UploadTgPacketRequest = Body()
) -> schemas.OKResponse:
    layer = request_obj.layer

    if layer not in GlobalVariables.layers_tlobjects:
        raise RequestValidationError(
            errors = [
                {
                    "loc": ["body", "layer"],
                    "msg": f"Layer {layer} is not supported",
                    "type": "value_error"
                }
            ]
        )

    try:
        auth_key, session_id, packet = request_obj.get_bytes()

    except ValueError:
        raise RequestValidationError(
            errors = [
                {
                    "loc": ["body", "auth_key", "session_id", "packet"],
                    "msg": "Not hex-encoded bytes",
                    "type": "value_error"
                }
            ]
        )

    tl_message = parse_tg_packet(
        packet = packet,
        auth_key = auth_key,
        session_id = session_id,
        tlobjects = GlobalVariables.layers_tlobjects[layer],
        core_objects = GlobalVariables.layers_coreobjects[layer]
    )

    if tl_message is None:
        raise RequestValidationError(
            errors = [
                {
                    "loc": ["body", "packet"],
                    "msg": "Invalid packet content",
                    "type": "value_error"
                }
            ]
        )

    is_tlobject_same_by_constructor_id = partial(
        _is_tlobject_same_by_constructor_id,
        needed_layers_tlobject_constructor_ids = GlobalVariables.needed_layers_tlobjects_constructor_ids[layer]
    )

    tg_obj = tl_message.obj  # type: ignore
    tg_objs: list[TLMessage]

    if is_tlobject_same_by_constructor_id(tg_obj, "MessageContainer"):  # type: ignore
        tg_objs = [  # type: ignore
            tl_message.obj  # type: ignore
            for tl_message in tg_obj.messages  # type: ignore
        ]

    else:
        tg_objs = [tg_obj]  # type: ignore

    for tg_obj in tg_objs:
        if is_tlobject_same_by_constructor_id(tg_obj, "GzipPacked"):  # type: ignore
            with BinaryReader(tg_obj.data) as reader:  # type: ignore
                tlobjects = GlobalVariables.layers_tlobjects[layer]
                core_objects = GlobalVariables.layers_coreobjects[layer]

                reader.tgread_object = partial(  # type: ignore
                    tgread_object,
                    reader = reader,
                    tlobjects = tlobjects,
                    core_objects = core_objects
                )

                tg_obj = reader.tgread_object()  # type: ignore

        tg_messages: list[tl_types.TypeMessage] = []
        # chats: list[tl_types.TypeChat] = []
        tg_users: list[tl_types.TypeUser] = []

        if is_tlobject_same_by_constructor_id(tg_obj, "Updates"):  # type: ignore
            for update in tg_obj.updates:  # type: ignore
                if is_tlobject_same_by_constructor_id(update, "UpdateNewChannelMessage"):  # type: ignore
                    tg_messages.append(update.message)  # type: ignore

            # chats.extend(tg_obj.chats)  # type: ignore
            tg_users.extend(tg_obj.users)  # type: ignore

        elif is_tlobject_same_by_constructor_id(tg_obj, "ChannelDifference") or is_tlobject_same_by_constructor_id(tg_obj, "ChannelDifferenceTooLong"):  # type: ignore
            tg_messages.extend(getattr(tg_obj, "new_messages", getattr(tg_obj, "messages")))  # type: ignore
            # chats.extend(tg_obj.chats)  # type: ignore
            tg_users.extend(tg_obj.users)  # type: ignore

        for message in tg_messages:
            if is_tlobject_same_by_constructor_id(message, "Message"):  # type: ignore
                if is_tlobject_same_by_constructor_id(message.peer_id, "PeerChannel") and is_tlobject_same_by_constructor_id(message.from_id, "PeerUser"):  # type: ignore
                    # tg_chat_obj = None  # type: ignore

                    # for tg_chat_obj_ in tg_chats:  # type: ignore
                    #     if is_tlobject_same_by_constructor_id(tg_chat_obj_, "Channel") and tg_chat_obj_.id == message.peer_id.channel_id:  # type: ignore
                    #         tg_chat_obj = tg_chat_obj_  # type: ignore
                    #         break

                    tg_user_obj = None

                    for tg_user_obj_ in tg_users:  # type: ignore
                        if is_tlobject_same_by_constructor_id(tg_user_obj_, "User") and tg_user_obj_.id == message.from_id.user_id:  # type: ignore
                            tg_user_obj = tg_user_obj_  # type: ignore
                            break

                    if tg_user_obj and tg_user_obj.bot:  # type: ignore
                        continue

                    tg_user_id = typing.cast(int, message.from_id.user_id)  # type: ignore
                    tg_chat_id = -1 * (typing.cast(int, message.peer_id.channel_id) + 1_000_000_000_000)  # type: ignore
                    tg_message_id = typing.cast(int, message.id)  # type: ignore
                    chat_or_user_added = False

                    db_result = (await db_session.execute(
                        sa.select(db.Chat, db.User)
                        .select_from(dummy_cte)
                        .outerjoin(db.Chat, db.Chat.tg_chat_id == tg_chat_id)
                        .outerjoin(db.User, db.User.tg_user_id == tg_user_id)
                    )).first()

                    db_chat, db_user = (
                        db_result.tuple()
                        if db_result
                        else
                        (None, None)
                    )

                    if not db_chat:
                        db_chat = db.Chat(
                            tg_chat_id = tg_chat_id
                        )

                        db_session.add(db_chat)

                        chat_or_user_added = True

                    if not db_user:
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
                        reply_to_tg_message_id = None

                        if is_tlobject_same_by_constructor_id(message.reply_to, "MessageReplyHeader") and not message.reply_to.reply_to_peer_id:  # type: ignore
                            reply_to_tg_message_id = typing.cast(int, message.reply_to.reply_to_msg_id)  # type: ignore

                        if chat_or_user_added:
                            await db_session.flush()

                        message_text = typing.cast(str | None, message.message)  # type: ignore

                        md_text: str | None

                        if message_text:
                            md_text = unparse_markdown(message_text, message.entities or [])  # type: ignore
                        else:
                            md_text = None

                        db_session.add(db.Message(
                            tg_chat_id = tg_chat_id,
                            tg_user_id = tg_user_id,
                            tg_message_id = tg_message_id,
                            reply_to_tg_message_id = reply_to_tg_message_id,
                            md_text = md_text,
                            sent_at = message.date,  # type: ignore
                            used_auth_key = auth_key,
                            used_session_id = session_id,
                            packet = packet,
                            chat = db_chat,
                            user = db_user
                        ))

    await db_session.commit()

    return schemas.OKResponse()
