from telethon import TelegramClient
from telethon.tl import types as tl_types, functions as tl_functions
from telethon.tl.core import GzipPacked
from telethon.network.mtprotosender import MTProtoSender
from telethon.tl.alltlobjects import LAYER
from telethon.extensions import BinaryReader
from telethon.errors import InvalidBufferError, AuthKeyNotFound, SecurityError, TypeNotFoundError
from httpx import AsyncClient
from functools import partial

import asyncio
import struct
import typing


SESSION_NAME = "userbot"
API_ID = 1234
API_HASH = "abcd"

FILTER_CHAT_IDS: list[int] | None = [
    -1001217010605,  # @durovschars
]

API_URL = "http://127.0.0.1:8192/api"
MAX_SEND_PACKETS_QUEUE_SIZE = 1000


send_packets_http_client = AsyncClient(
    base_url = API_URL
)

SEND_PACKETS_QUEUE_T = asyncio.Queue[tuple[bytes, bytes, bytes]]


async def custom_sender_recv_loop(self: MTProtoSender, send_packets_queue: SEND_PACKETS_QUEUE_T, filter_chat_ids: list[int] | None=None) -> None:
    auth_key: bytes | None = None
    session_id: bytes | None = None

    while self._user_connected and not self._reconnecting:  # type: ignore
        self._log.debug('Receiving items from the network...')  # type: ignore
        try:
            body = typing.cast(bytes, await self._connection.recv())  # type: ignore
        except asyncio.CancelledError:
            raise  # bypass except Exception
        except (IOError, asyncio.IncompleteReadError) as e:
            self._log.info('Connection closed while receiving data: %s', e)  # type: ignore
            self._start_reconnect(e)  # type: ignore
            return
        except InvalidBufferError as e:
            if e.code == 429:
                self._log.warning('Server indicated flood error at transport level: %s', e)  # type: ignore
                await self._disconnect(error=e)  # type: ignore
            else:
                self._log.exception('Server sent invalid buffer')  # type: ignore
                self._start_reconnect(e)  # type: ignore
            return
        except Exception as e:
            self._log.exception('Unhandled error while receiving data')  # type: ignore
            self._start_reconnect(e)  # type: ignore
            return

        try:
            message = self._state.decrypt_message_data(body)  # type: ignore
            if message is None:
                continue  # this message is to be ignored
        except TypeNotFoundError as e:
            # Received object which we don't know how to deserialize
            self._log.info('Type %08x not found, remaining data %r',  # type: ignore
                            e.invalid_constructor_id, e.remaining)
            continue
        except SecurityError as e:
            # A step while decoding had the incorrect data. This message
            # should not be considered safe and it should be ignored.
            self._log.warning('Security error while unpacking a '  # type: ignore
                                'received message: %s', e)
            continue
        except BufferError as e:
            if isinstance(e, InvalidBufferError) and e.code == 404:
                self._log.info('Server does not know about the current auth key; the session may need to be recreated')  # type: ignore
                await self._disconnect(error=AuthKeyNotFound())  # type: ignore
            else:
                self._log.warning('Invalid buffer %s', e)  # type: ignore
                self._start_reconnect(e)  # type: ignore
            return
        except Exception as e:
            self._log.exception('Unhandled error while decrypting data')  # type: ignore
            self._start_reconnect(e)  # type: ignore
            return

        if auth_key and session_id:
            constructor_id = getattr(message.obj, "CONSTRUCTOR_ID", None)  # type: ignore

            if constructor_id == GzipPacked.CONSTRUCTOR_ID:
                with BinaryReader(message.obj.data) as reader:  # type: ignore
                    message.obj = reader.tgread_object()
                    constructor_id = getattr(message.obj, "CONSTRUCTOR_ID", None)  # type: ignore

            if constructor_id == tl_types.Updates.CONSTRUCTOR_ID:
                send_packet = not filter_chat_ids

                if not send_packet:
                    for update in typing.cast(tl_types.Updates, message.obj).updates:
                        if isinstance(update, tl_types.UpdateNewChannelMessage):
                            message_ = update.message

                            if isinstance(message_, tl_types.Message):
                                if isinstance(message_.peer_id, tl_types.PeerChannel) and isinstance(message_.from_id, tl_types.PeerUser):
                                    tg_chat_obj: tl_types.Channel | None = None

                                    for tg_chat_obj_ in message.obj.chats:  # type: ignore
                                        if isinstance(tg_chat_obj_, tl_types.Channel) and tg_chat_obj_.id == message_.peer_id.channel_id:
                                            tg_chat_obj = tg_chat_obj_
                                            break

                                    if tg_chat_obj is not None:
                                        tg_chat_id = -1 * (message_.peer_id.channel_id + 1_000_000_000_000)

                                        if tg_chat_id in filter_chat_ids:  # type: ignore
                                            send_packet = True
                                            break

                if send_packet:
                    # print(f"Processing packet: {body.hex()}")  # type: ignore
                    # print(f"Auth key: {auth_key.hex()}")  # type: ignore
                    # print(f"Session ID: {session_id.hex()}")
                    # print(f"Message: {message}")

                    send_packets_queue.put_nowait((auth_key, session_id, body,))

        elif self._state and self._state.auth_key and self._state.auth_key.key and self._state.id:  # type: ignore
            try:
                auth_key = typing.cast(bytes, self._state.auth_key.key)  # type: ignore
                session_id = struct.pack("q", self._state.id)  # type: ignore

            except Exception:
                pass

        try:
            await self._process_message(message)  # type: ignore
        except Exception:
            self._log.exception('Unhandled error while processing msgs')  # type: ignore


async def send_packets_loop(send_packets_queue: SEND_PACKETS_QUEUE_T) -> None:
    while True:
        auth_key, session_id, packet = await send_packets_queue.get()

        payload = {
            "layer": LAYER,
            "auth_key": auth_key.hex(),
            "session_id": session_id.hex(),
            "packet": packet.hex()
        }

        try:
            await send_packets_http_client.post("/upload_tg_packet", json=payload)

        except Exception as ex:
            print(f"Error sending packet: {ex} | Payload: {payload}")

        finally:
            send_packets_queue.task_done()


async def setup_client_custom_sender(client: TelegramClient) -> None:
    if client.is_connected():
        raise RuntimeError("Client is already connected")

    response = (await send_packets_http_client.get("/supported_layers")).json()

    if LAYER not in response["supported_layers"]:
        raise RuntimeError(f"Layer {LAYER} is not supported by the server")

    send_packets_queue = SEND_PACKETS_QUEUE_T(maxsize=MAX_SEND_PACKETS_QUEUE_SIZE)

    asyncio.create_task(send_packets_loop(send_packets_queue))

    client._sender._recv_loop = partial(custom_sender_recv_loop, client._sender, send_packets_queue, FILTER_CHAT_IDS)  # type: ignore


async def main() -> None:
    print("Using layer:", LAYER)

    client = TelegramClient(
        session = SESSION_NAME,
        api_id = API_ID,
        api_hash = API_HASH,
        receive_updates = True
    )

    await setup_client_custom_sender(client)

    await client.start()  # type: ignore
    await client.connect()

    if FILTER_CHAT_IDS:
        print("Preparing to listen for messages...")

        for chat_id in FILTER_CHAT_IDS:
            input_entity = await client.get_input_entity(chat_id)

            if not isinstance(input_entity, tl_types.InputPeerChannel):
                raise ValueError(f"Expected InputPeerChannel, got {type(input_entity)}")

            pts = typing.cast(int, (await client(tl_functions.channels.GetFullChannelRequest(  # type: ignore
                channel = input_entity  # type: ignore
            ))).full_chat.pts)

            await client(tl_functions.updates.GetChannelDifferenceRequest(  # type: ignore
                channel = tl_types.InputChannel(
                    channel_id = input_entity.channel_id,
                    access_hash = input_entity.access_hash
                ),
                filter = tl_types.ChannelMessagesFilterEmpty(),
                pts = pts,
                limit = 100,
                force = False
            ))

    # NOTE: issue: not all Updates being received.
    #  probably, because of not updating pts.
    #  possible fix: monitor received packets for constrctors:
    #  Difference & DifferenceSlice
    #  and probably this also won't work, cause those objects containts
    #  updates and messages fields, so there is a way to only encrypt
    #  Updates with our own solution, which can be used against us.

    print("Listening for messages...")

    await client.run_until_disconnected()  # type: ignore


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
