from pathlib import Path


ENCODING = "utf-8"

APP_VERSION = "0.1.0"

NEEDED_LAYERS_TLOBJECT_NAMES = [
    "Updates",
    "UpdateNewChannelMessage",
    "ChannelDifference",
    "ChannelDifferenceTooLong",
    "MessageContainer",
    "Message",
    "PeerChannel",
    "PeerUser",

    "GzipPacked",
    "User",
    "Chat",
    "Channel",
    "MessageEmpty",
    "MessageEntityBankCard",
    "MessageEntityBlockquote",
    "MessageEntityBold",
    "MessageEntityBotCommand",
    "MessageEntityCashtag",
    "MessageEntityCode",
    "MessageEntityCustomEmoji",
    "MessageEntityEmail",
    "MessageEntityHashtag",
    "MessageEntityItalic",
    "MessageEntityMention",
    "MessageEntityMentionName",
    "MessageEntityPhone",
    "MessageEntityPre",
    "MessageEntitySpoiler",
    "MessageEntityStrike",
    "MessageEntityTextUrl",
    "MessageEntityUnderline",
    "MessageEntityUnknown",
    "MessageEntityUrl",
    "MessageReplies",
    "MessageReplyHeader",
    "MessageService",
    "UserProfilePhotoEmpty",
    "UserProfilePhoto",
    "UserStatusEmpty",
    "UserStatusOnline",
    "UserStatusOffline",
    "UserStatusRecently",
    "UserStatusLastWeek",
    "UserStatusLastMonth",
    "EmojiStatusEmpty",
    "EmojiStatus",
    "EmojiStatusCollectible",
    "PeerColor",
    "ChatPhotoEmpty",
    "ChatPhoto",
    "ChatBannedRights",
]


PARENT_DIRPATH = Path(__file__).parent.parent
LOGS_DIRPATH = PARENT_DIRPATH / "logs"
LAYERS_DIRPATH = PARENT_DIRPATH / "layers"

LOG_FILENAME = "log.txt"


if not LOGS_DIRPATH.exists():
    LOGS_DIRPATH.mkdir()
