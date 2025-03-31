from telethon.tl import types
from telethon.tl.types import TypeMessageEntity
from enum import Enum
from struct import unpack

import re


SMP_RE = re.compile(r"[\U00010000-\U0010FFFF]")


def add_surrogates(text: str) -> str:
    return SMP_RE.sub(
        lambda match: "".join(chr(i) for i in unpack("<HH", match.group().encode("utf-16le"))),
        text
    )

def remove_surrogates(text: str) -> str:
    return text.encode("utf-16", "surrogatepass").decode("utf-16")

def replace_once(source: str, old: str, new: str, start: int) -> str:
    return source[:start] + source[start:].replace(old, new, 1)

def within_surrogate(text: str, index: int, *, length: int | None=None) -> bool:
    if length is None:
        length = len(text)

    return (
        1 < index < len(text) and
        '\ud800' <= text[index - 1] <= '\udbff' and
        '\ud800' <= text[index] <= '\udfff'
    )


BOLD_DELIM = "**"
ITALIC_DELIM = "__"
UNDERLINE_DELIM = "--"
STRIKE_DELIM = "~~"
SPOILER_DELIM = "||"
CODE_DELIM = "`"
PRE_DELIM = "```"
BLOCKQUOTE_DELIM = ">"
BLOCKQUOTE_EXPANDABLE_DELIM = "**>"

MARKDOWN_RE = re.compile(r"({d})".format(
    d = "|".join(
        [
            "".join(i)
            for i in [
                [rf"\{j}" for j in i]
                for i in [
                    PRE_DELIM,
                    CODE_DELIM,
                    STRIKE_DELIM,
                    UNDERLINE_DELIM,
                    ITALIC_DELIM,
                    BOLD_DELIM,
                    SPOILER_DELIM
                ]
            ]
        ]
    )
))
URL_RE = re.compile(r"(!?)\[(.+?)\]\((.+?)\)")

OPENING_TAG = "<{}>"
CLOSING_TAG = "</{}>"
URL_MARKUP = '<a href="{}">{}</a>'
EMOJI_MARKUP = '<emoji id={}>{}</emoji>'
FIXED_WIDTH_DELIMS = [CODE_DELIM, PRE_DELIM]
CODE_TAG_RE = re.compile(r"<code>.*?</code>")


class MessageEntityType(Enum):
    MENTION = types.MessageEntityMention
    HASHTAG = types.MessageEntityHashtag
    CASHTAG = types.MessageEntityCashtag
    BOT_COMMAND = types.MessageEntityBotCommand
    URL = types.MessageEntityUrl
    EMAIL = types.MessageEntityEmail
    PHONE_NUMBER = types.MessageEntityPhone
    BOLD = types.MessageEntityBold
    ITALIC = types.MessageEntityItalic
    UNDERLINE = types.MessageEntityUnderline
    STRIKETHROUGH = types.MessageEntityStrike
    SPOILER = types.MessageEntitySpoiler
    CODE = types.MessageEntityCode
    PRE = types.MessageEntityPre
    BLOCKQUOTE = types.MessageEntityBlockquote
    EXPANDABLE_BLOCKQUOTE = types.MessageEntityBlockquote
    TEXT_LINK = types.MessageEntityTextUrl
    TEXT_MENTION = types.MessageEntityMentionName
    BANK_CARD = types.MessageEntityBankCard
    CUSTOM_EMOJI = types.MessageEntityCustomEmoji
    UNKNOWN = types.MessageEntityUnknown

MESSAGE_ENTITY_TYPE_NAMES = {
    member.value.__name__: member
    for member in MessageEntityType
}

DELIMITERS = {
    MessageEntityType.BOLD: BOLD_DELIM,
    MessageEntityType.ITALIC: ITALIC_DELIM,
    MessageEntityType.UNDERLINE: UNDERLINE_DELIM,
    MessageEntityType.STRIKETHROUGH: STRIKE_DELIM,
    MessageEntityType.CODE: CODE_DELIM,
    MessageEntityType.PRE: PRE_DELIM,
    MessageEntityType.BLOCKQUOTE: BLOCKQUOTE_DELIM,
    MessageEntityType.EXPANDABLE_BLOCKQUOTE: BLOCKQUOTE_EXPANDABLE_DELIM,
    MessageEntityType.SPOILER: SPOILER_DELIM
}

def get_entity_type(entity: TypeMessageEntity) -> MessageEntityType | None:
    return MESSAGE_ENTITY_TYPE_NAMES.get(type(entity).__name__, None)


def unparse_markdown(text: str, entities: list[TypeMessageEntity]) -> str:
    text = add_surrogates(text)

    insert_at: list[tuple[int, int, str]] = []

    for i, entity in enumerate(entities):
        s = entity.offset
        e = entity.offset + entity.length
        entity_type = get_entity_type(entity)  # type: ignore
        delimiter = DELIMITERS.get(entity_type, None) if entity_type is not None else None
        if delimiter:
            if entity_type == MessageEntityType.PRE:
                inside_blockquote = any(
                    blk_entity.offset <= s < blk_entity.offset + blk_entity.length and
                    blk_entity.offset < e <= blk_entity.offset + blk_entity.length
                    for blk_entity in entities
                    if get_entity_type(blk_entity) == MessageEntityType.BLOCKQUOTE
                )
                is_expandable = any(
                    blk_entity.offset <= s < blk_entity.offset + blk_entity.length and
                    blk_entity.offset < e <= blk_entity.offset + blk_entity.length and
                    blk_entity.collapsed  # type: ignore
                    for blk_entity in entities
                    if get_entity_type(blk_entity) == MessageEntityType.BLOCKQUOTE
                )
                if inside_blockquote:
                    if is_expandable:
                        if entity.language:  # type: ignore
                            open_delimiter = f"{delimiter}{entity.language}\n**>"  # type: ignore
                        else:
                            open_delimiter = f"{delimiter}\n**>"
                        close_delimiter = f"\n**>{delimiter}"
                    else:
                        if entity.language:  # type: ignore
                            open_delimiter = f"{delimiter}{entity.language}\n>"  # type: ignore
                        else:
                            open_delimiter = f"{delimiter}\n>"
                        close_delimiter = f"\n>{delimiter}"
                else:
                    open_delimiter = delimiter
                    close_delimiter = delimiter
                insert_at.append((s, i, open_delimiter))
                insert_at.append((e, -i, close_delimiter))
            elif entity_type != MessageEntityType.BLOCKQUOTE and entity_type != MessageEntityType.EXPANDABLE_BLOCKQUOTE:
                open_delimiter = delimiter
                close_delimiter = delimiter
                insert_at.append((s, i, open_delimiter))
                insert_at.append((e, -i, close_delimiter))
            else:
                # Handle multiline blockquotes
                text_subset = text[s:e]
                lines = text_subset.splitlines()
                for line_num, _ in enumerate(lines):
                    line_start = s + sum(len(ll) + 1 for ll in lines[:line_num])
                    if entity.collapsed:  # type: ignore
                        insert_at.append((line_start, i, BLOCKQUOTE_EXPANDABLE_DELIM))
                    else:
                        insert_at.append((line_start, i, BLOCKQUOTE_DELIM))
                # No closing delimiter for blockquotes
        else:
            url = None
            is_emoji = False
            if entity_type == MessageEntityType.TEXT_LINK:
                url = entity.url  # type: ignore
            elif entity_type == MessageEntityType.TEXT_MENTION:
                url = f'tg://user?id={entity.user_id}'  # type: ignore
            elif entity_type == MessageEntityType.CUSTOM_EMOJI:
                url = f"tg://emoji?id={entity.document_id}"  # type: ignore
                is_emoji = True
            if url:
                if is_emoji:
                    insert_at.append((s, i, '!['))
                else:
                    insert_at.append((s, i, '['))
                insert_at.append((e, -i, f']({url})'))

    insert_at.sort(key=lambda t: (t[0], t[1]))
    while insert_at:
        at, _, what = insert_at.pop()

        # If we are in the middle of a surrogate nudge the position by -1.
        # Otherwise we would end up with malformed text and fail to encode.
        # For example of bad input: "Hi \ud83d\ude1c"
        # https://en.wikipedia.org/wiki/UTF-16#U+010000_to_U+10FFFF
        while within_surrogate(text, at):
            at += 1

        text = text[:at] + what + text[at:]

    return remove_surrogates(text)
