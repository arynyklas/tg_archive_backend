from telethon import TelegramClient
from telethon.tl import types as tl_types, functions as tl_functions
from telethon.tl.core import GzipPacked, MessageContainer, TLMessage
from telethon.network.mtprotosender import MTProtoSender
from telethon.tl.alltlobjects import LAYER
from telethon.extensions import BinaryReader
from telethon.errors import InvalidBufferError, AuthKeyNotFound, SecurityError, TypeNotFoundError
from httpx import AsyncClient
from functools import partial

import asyncio
import struct
import typing

import config


API_URL = "http://127.0.0.1:8192/api"
MAX_SEND_PACKETS_QUEUE_SIZE = 1000
GET_DIFFERENCE_LIMIT = 10


send_packets_http_client = AsyncClient(
    base_url = API_URL
)

SEND_PACKETS_QUEUE_T = asyncio.Queue[tuple[bytes, bytes, bytes]]


def _should_send_packet_by_message(message: tl_types.TypeMessage, chats: list[tl_types.TypeChat], filter_chat_ids: list[int] | None=None) -> bool:
    if isinstance(message, tl_types.Message) and isinstance(message.peer_id, tl_types.PeerChannel) and isinstance(message.from_id, tl_types.PeerUser):
        tg_chat_obj: tl_types.Channel | None = None

        for tg_chat_obj_ in chats:
            if isinstance(tg_chat_obj_, tl_types.Channel) and tg_chat_obj_.id == message.peer_id.channel_id:
                tg_chat_obj = tg_chat_obj_
                break

        if tg_chat_obj is not None:
            tg_chat_id = -1 * (message.peer_id.channel_id + 1_000_000_000_000)

            if filter_chat_ids and tg_chat_id in filter_chat_ids:
                return True

    return False


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
            tl_message = self._state.decrypt_message_data(body)  # type: ignore
            if tl_message is None:
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
            tg_obj = tl_message.obj  # type: ignore
            send_packet = False
            tg_objs: list[TLMessage]

            if isinstance(tg_obj, MessageContainer):
                tg_objs = [
                    tl_message.obj  # type: ignore
                    for tl_message in tg_obj.messages  # type: ignore
                ]

            else:
                tg_objs = [tg_obj]  # type: ignore

            for tg_obj in tg_objs:
                constructor_id = getattr(tg_obj, "CONSTRUCTOR_ID", None)  # type: ignore

                if constructor_id == GzipPacked.CONSTRUCTOR_ID:
                    with BinaryReader(tg_obj.data) as reader:  # type: ignore
                        tg_obj = reader.tgread_object()  # type: ignore
                        constructor_id = getattr(tg_obj, "CONSTRUCTOR_ID", None)  # type: ignore

                if isinstance(tg_obj, (tl_types.updates.ChannelDifference, tl_types.updates.ChannelDifferenceTooLong)):
                    send_packet = not filter_chat_ids

                    if not send_packet:
                        for message in getattr(tg_obj, "new_messages", getattr(tg_obj, "messages")):
                            send_packet = _should_send_packet_by_message(message, tg_obj.chats, filter_chat_ids)

                            if send_packet:
                                break

                if not send_packet and isinstance(tg_obj, tl_types.Updates):
                    send_packet = not filter_chat_ids

                    if not send_packet:
                        for update in tg_obj.updates:
                            if isinstance(update, tl_types.UpdateNewChannelMessage):  # type: ignore
                                send_packet = _should_send_packet_by_message(update.message, tg_obj.chats, filter_chat_ids)

                                if send_packet:
                                    break

                if send_packet:
                    break

            if send_packet:
                send_packets_queue.put_nowait((auth_key, session_id, body,))

        elif self._state and self._state.auth_key and self._state.auth_key.key and self._state.id:  # type: ignore
            try:
                auth_key = typing.cast(bytes, self._state.auth_key.key)  # type: ignore
                session_id = struct.pack("q", self._state.id)  # type: ignore

            except Exception:
                pass

        try:
            await self._process_message(tl_message)  # type: ignore
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


async def setup_client_custom_sender(client: TelegramClient, filter_chat_ids: list[int] | None=None) -> None:
    if client.is_connected():
        raise RuntimeError("Client is already connected")

    response = (await send_packets_http_client.get("/supported_layers")).json()

    if LAYER not in response["supported_layers"]:
        raise RuntimeError(f"Layer {LAYER} is not supported by the server")

    send_packets_queue = SEND_PACKETS_QUEUE_T(maxsize=MAX_SEND_PACKETS_QUEUE_SIZE)

    asyncio.create_task(send_packets_loop(send_packets_queue))

    client._sender._recv_loop = partial(custom_sender_recv_loop, client._sender, send_packets_queue, filter_chat_ids)  # type: ignore


async def filter_chat_ids_difference_checker(client: TelegramClient, input_peer_channels: list[tl_types.InputPeerChannel]) -> None:
    pts_dict: dict[int, int] = {}

    async def _per_channel_difference_checker(input_channel: tl_types.InputChannel) -> None:
        while True:
            r: tl_types.updates.ChannelDifferenceEmpty | tl_types.updates.ChannelDifference | tl_types.updates.ChannelDifferenceTooLong = await client(tl_functions.updates.GetChannelDifferenceRequest(  # type: ignore
                channel = input_channel,
                filter = tl_types.ChannelMessagesFilterEmpty(),
                pts = pts_dict[input_channel.channel_id],
                limit = GET_DIFFERENCE_LIMIT,
                force = False
            ))

            pts_dict[input_channel.channel_id] = getattr(r, "pts", pts_dict[input_channel.channel_id])  # type: ignore

            await asyncio.sleep(r.timeout or 1)  # type: ignore

    input_channels: list[tl_types.InputChannel] = []

    for input_peer_channel in input_peer_channels:
        input_channel = tl_types.InputChannel(
            channel_id = input_peer_channel.channel_id,
            access_hash = input_peer_channel.access_hash
        )

        input_channels.append(input_channel)

        full_channel = await client(tl_functions.channels.GetFullChannelRequest(  # type: ignore
            channel = input_channel
        ))

        pts_dict[input_peer_channel.channel_id] = typing.cast(int, full_channel.full_chat.pts)  # type: ignore

    await asyncio.gather(*[
        _per_channel_difference_checker(input_channel)
        for input_channel in input_channels
    ])


async def main() -> None:
    print("Using layer:", LAYER)

    client = TelegramClient(
        session = config.SESSION_NAME,
        api_id = config.API_ID,
        api_hash = config.API_HASH,
        receive_updates = True
    )

    await setup_client_custom_sender(client, config.FILTER_CHAT_IDS)

    await client.start()  # type: ignore

    if config.FILTER_CHAT_IDS:
        print("Preparing to listening for messages...")

        input_peer_channels: list[tl_types.InputPeerChannel] = []

        for chat_id in config.FILTER_CHAT_IDS:
            input_peer = await client.get_input_entity(chat_id)

            if not isinstance(input_peer, tl_types.InputPeerChannel):
                raise ValueError(f"Expected InputPeerChannel, got {type(input_peer)} for chat_id {chat_id!r}")

            input_peer_channels.append(input_peer)

        asyncio.create_task(filter_chat_ids_difference_checker(client, input_peer_channels))

    print("Listening for messages...")

    await client.run_until_disconnected()  # type: ignore


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
