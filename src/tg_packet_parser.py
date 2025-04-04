from telethon.crypto import AES
from telethon.extensions import BinaryReader
from telethon.tl import TLObject
from telethon.tl.core import TLMessage
from telethon.errors import TypeNotFoundError
from hashlib import sha256, sha1
from functools import partial

import struct
import typing


def _calc_key(auth_key: bytes, msg_key: bytes) -> tuple[bytes, bytes]:
    x = 8
    sha256a = sha256(msg_key + auth_key[x: x + 36]).digest()
    sha256b = sha256(auth_key[x + 40:x + 76] + msg_key).digest()

    aes_key = sha256a[:8] + sha256b[8:24] + sha256a[24:32]
    aes_iv = sha256b[:8] + sha256a[8:24] + sha256b[24:32]

    return (aes_key, aes_iv)


POSSIBLE_READ_RESSULT_T = TLObject | bool | list["POSSIBLE_READ_RESSULT_T"] | None

def tgread_object(reader: BinaryReader, tlobjects: dict[int, TLObject], core_objects: dict[int, TLObject]) -> POSSIBLE_READ_RESSULT_T:
    constructor_id = reader.read_int(signed=False)
    clazz = tlobjects.get(constructor_id, None)

    if clazz is None:
        if constructor_id == 0x997275b5:  # boolTrue
            return True

        elif constructor_id == 0xbc799737:  # boolFalse
            return False

        elif constructor_id == 0x1cb5c415:  # Vector
            return [
                tgread_object(reader, tlobjects, core_objects)
                for _ in range(reader.read_int())
            ]

        clazz = core_objects.get(constructor_id, None)

        if clazz is None:
            reader.seek(-4)  # type: ignore
            pos = reader.tell_position()
            error = TypeNotFoundError(constructor_id, reader.read())
            reader.set_position(pos)  # type: ignore
            raise error

    return clazz.from_reader(reader)  # type: ignore


def decrypt_message_data(body: bytes, auth_key: bytes, auth_key_id: bytes, session_id: bytes, tlobjects: dict[int, TLObject], core_objects: dict[int, TLObject]) -> TLMessage:
    if len(body) < 8:
        raise ValueError("Body is too short")

    # TODO Check salt, session_id and sequence_number
    if body[:8] != auth_key_id:
        raise ValueError('Packet contains an invalid auth key')

    msg_key = body[8:24]
    aes_key, aes_iv = _calc_key(auth_key, msg_key)
    body = typing.cast(bytes, AES.decrypt_ige(body[24:], aes_key, aes_iv))  # type: ignore

    our_key = sha256(auth_key[96:96 + 32] + body)

    if msg_key != our_key.digest()[8:24]:
        raise ValueError("Packet's msg_key doesn't match with expected one")

    reader = BinaryReader(body)
    reader.read_long()  # remote_salt

    if struct.pack("q", reader.read_long()) != session_id:
        raise ValueError('Packet contains a wrong session ID')

    remote_msg_id = reader.read_long()

    if remote_msg_id % 2 != 1:
        raise ValueError('Packet contains an even msg_id')

    remote_sequence = reader.read_int()
    reader.read_int()  # msg_len for the inner object, padding ignored

    reader.tgread_object = partial(  # type: ignore
        tgread_object,
        reader = reader,
        tlobjects = tlobjects,
        core_objects = core_objects
    )

    try:
        obj = reader.tgread_object()  # type: ignore
    except BufferError as ex:
        raise RuntimeError("Needed object not found") from ex

    return TLMessage(remote_msg_id, remote_sequence, obj)  # type: ignore


def parse_tg_packet(packet: bytes, auth_key: bytes, session_id: bytes, tlobjects: dict[int, TLObject], core_objects: dict[int, TLObject]) -> TLMessage | None:
    auth_key_id = sha1(auth_key).digest()[-8:]

    # try:
    return decrypt_message_data(
        body = packet,
        auth_key = auth_key,
        auth_key_id = auth_key_id,
        session_id = session_id,
        tlobjects = tlobjects,
        core_objects = core_objects
    )

    # except Exception:
    #     return None
