from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

import sqlalchemy as sa
import typing

from .base import BaseModel


t_idpk = typing.Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
tg_id_type = BigInteger


class Chat(BaseModel):
    __tablename__ = "chats"

    id: Mapped[t_idpk] = mapped_column(init=False)
    tg_chat_id: Mapped[int] = mapped_column(tg_id_type, index=True, unique=True, nullable=False)

    messages: Mapped[list["Message"]] = relationship(default_factory=list, back_populates="chat", lazy="noload")


class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[t_idpk] = mapped_column(init=False)
    tg_user_id: Mapped[int] = mapped_column(tg_id_type, index=True, unique=True, nullable=False)

    messages: Mapped[list["Message"]] = relationship(default_factory=list, back_populates="user", lazy="noload")


class Message(BaseModel):
    __tablename__ = "messages"
    __table_args__ = (
        sa.UniqueConstraint("tg_chat_id", "tg_message_id", name="uq_tg_chat_id_tg_message_id"),
    )

    id: Mapped[t_idpk] = mapped_column(init=False)
    tg_chat_id: Mapped[int] = mapped_column(tg_id_type, ForeignKey("chats.tg_chat_id"), index=True, nullable=False)
    tg_user_id: Mapped[int | None] = mapped_column(tg_id_type, ForeignKey("users.tg_user_id"), index=True, nullable=True)
    tg_message_id: Mapped[int] = mapped_column(tg_id_type, index=True, unique=True, nullable=False)
    md_text: Mapped[str | None] = mapped_column(nullable=True)
    sent_at: Mapped[datetime] = mapped_column(nullable=False)
    used_auth_key: Mapped[bytes] = mapped_column(nullable=False)
    used_session_id: Mapped[bytes] = mapped_column(nullable=False)
    packet: Mapped[bytes] = mapped_column(nullable=False)

    chat: Mapped[typing.Optional["Chat"]] = relationship(default=None, back_populates="messages", lazy="noload")
    user: Mapped[typing.Optional["User"]] = relationship(default=None, back_populates="messages", lazy="noload")
