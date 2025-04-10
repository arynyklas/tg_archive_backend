from pydantic import Field, field_validator
from datetime import datetime
from functools import partial

import typing

# from . import admin  # type: ignore
from .base import BaseModel, BaseRequest, BaseResponse, Timestamp


DICT_DATA_T = dict[str, typing.Any]
OKResponse = BaseResponse

MODEL_TIMESTAMP_T = int | Timestamp | datetime
Field_timestamp = partial(Field, examples=[1735689601])


LAYER_EXAMPLES = [
    201,
]


class SupportedLayersResponse(BaseResponse):
    supported_layers: list[int] = Field(
        default_factory = list,
        description = "List of supported layers",
        examples = [LAYER_EXAMPLES]
    )


class UploadTgPacketRequest(BaseRequest):
    layer: int = Field(
        ...,
        description = "Telegram MTProto layer",
        examples = LAYER_EXAMPLES
    )

    auth_key: str = Field(
        ...,
        description = "Auth key used to get the packet (hex)"
    )

    session_id: str = Field(
        ...,
        description = "Session ID used to get the packet (hex)"
    )

    packet: str = Field(
        ...,
        description = "Packet data (hex)"
    )

    def get_bytes(self) -> tuple[bytes, bytes, bytes]:
        try:
            return (
                bytes.fromhex(self.auth_key),
                bytes.fromhex(self.session_id),
                bytes.fromhex(self.packet)
            )

        except Exception:
            raise ValueError("Invalid hex string")


class Message(BaseModel):
    id: int = Field(
        ...,
        description = "Message ID"
    )

    tg_chat_id: int = Field(
        ...,
        description = "Telegram chat ID"
    )

    tg_user_id: int | None = Field(
        ...,
        description = "Telegram user ID"
    )

    tg_message_id: int = Field(
        ...,
        description = "Telegram message ID"
    )

    reply_to_tg_message_id: int | None = Field(
        ...,
        description = "Telegram message ID of the message this message is replying to"
    )

    md_text: str | None = Field(
        ...,
        description = "Markdown text of the message"
    )

    sent_at: MODEL_TIMESTAMP_T = Field_timestamp(
        ...,
        description = "Datetime when the message was sent (UTC)"
    )

    used_auth_key: str = Field(
        ...,
        description = "Auth key used to get the packet (hex)"
    )

    used_session_id: str = Field(
        ...,
        description = "Session ID used to get the packet (hex)"
    )

    packet: str = Field(
        ...,
        description = "Packet data (hex)"
    )

    inserted_at: MODEL_TIMESTAMP_T = Field_timestamp(
        ...,
        description = "Datetime when the message was inserted into the database (UTC)"
    )

    @field_validator("sent_at", "inserted_at", mode="before")
    @classmethod
    def validate_dt(cls, value: Timestamp) -> int:
        return Timestamp.validate(value)


class ListMessages(BaseResponse):
    messages: list[Message] = Field(
        ...,
        description = "List of messages"
    )

    # has_next: bool = Field(
    #     ...,
    #     description = "True if there are more messages to fetch"
    # )
