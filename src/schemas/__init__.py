from pydantic import Field, field_validator
from datetime import datetime
from functools import partial

import typing

# from . import admin  # type: ignore
from .base import BaseModel, BaseRequest, BaseResponse, Timestamp


DICT_DATA_T = dict[str, typing.Any]
OKResponse = BaseResponse
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


class GetMessagesRequest(BaseRequest):
    chat_id: int | None = Field(
        default = None,
        description = "Telegram chat ID"
    )

    user_id: int | None = Field(
        default = None,
        description = "Telegram user ID"
    )

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
        None,
        description = "Telegram user ID"
    )

    tg_message_id: int = Field(
        ...,
        description = "Telegram message ID"
    )

    md_text: str | None = Field(
        None,
        description = "Markdown text of the message"
    )

    sent_at: int | Timestamp | datetime = Field_timestamp(
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

    inserted_at: int | Timestamp | datetime = Field_timestamp(
        ...,
        description = "Datetime when the message was inserted into the database (UTC)"
    )

    @field_validator("sent_at", "inserted_at", mode="before")
    @classmethod
    def validate_dt(cls, value: Timestamp) -> int:
        return Timestamp.validate(value)


class ListMessages(BaseResponse):
    messages: list[Message] = Field(
        default_factory = list,
        description = "List of messages"
    )
