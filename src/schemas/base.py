from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

import typing


class BaseResponse(BaseModel):
    model_config = ConfigDict(
        extra = "allow"
    )

    ok: bool = Field(default=True)


class BaseRequest(BaseModel):
    model_config = ConfigDict(
        extra = "forbid"
    )


class BaseCustomizableModel(BaseModel):
    model_config = ConfigDict(
        extra = "allow"
    )


class Timestamp(int):
    @classmethod
    def __get_validators__(cls):  # type: ignore
        yield cls.validate  # type: ignore

    @classmethod
    def validate(cls, value: typing.Any, _: typing.Any=None) -> int:
        if isinstance(value, datetime):
            return int(value.timestamp())
        if isinstance(value, (int, float)):
            return int(value)

        raise TypeError("Timestamp must be a datetime or an int/float representing a timestamp")


__all__ = (
    "BaseResponse",
    "BaseRequest",
    "BaseCustomizableModel",
    "Timestamp",
)
