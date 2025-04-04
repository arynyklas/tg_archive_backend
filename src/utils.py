from time import time
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler

import logging
import typing


DEFAULT_LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"

T = typing.TypeVar("T")
K = typing.TypeVar("K")
V = typing.TypeVar("V")

UTC_TIMEZONE = timezone.utc


def get_float_timestamp() -> float:
    return time()

def get_int_timestamp() -> int:
    return int(get_float_timestamp())

def get_datetime_utcnow() -> datetime:
    return datetime.now(tz=UTC_TIMEZONE)

def get_datetime_utc_from_timestamp(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=UTC_TIMEZONE)


def get_logger(name: str, filepath: Path, file_level: int | str, console_level: int | str) -> logging.Logger:
    logger = logging.getLogger(name)

    default_formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    file_handler = RotatingFileHandler(
        filename = filepath,
        mode = "a",
        maxBytes = 26_214_400,
        backupCount = 1_000,
        encoding = "utf-8"
    )

    file_handler.setLevel(file_level)
    file_handler.setFormatter(default_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(default_formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)

    logger.setLevel(min(file_handler.level, console_handler.level))

    return logger


def merge_dicts(*dicts: dict[K, V]) -> dict[K, V]:
    result: dict[K, V] = {}

    for dict_ in dicts:
        result.update(dict_)

    return result
