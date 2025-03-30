from fastapi import status
from pydantic.dataclasses import dataclass as _dataclass
from typing_extensions import Self

import typing


@_dataclass
class BaseError(Exception):
    status_code: int
    description: str

    @property
    def as_content(self) -> dict[str, typing.Any]:
        return {
            "ok": False,
            **{
                key: getattr(self, key)  # type: ignore
                for key in self.__pydantic_fields__.keys()  # type: ignore
                if key != "key"
            }
        }

    @property
    def as_openapi(self) -> dict[int | str, dict[str, typing.Any]]:
        return {
            self.status_code: {
                "description": self.description,
                "content": {
                    "application/json": {
                        "example": self.as_content
                    }
                }
            }
        }

    def update_description(self, description: str) -> Self:
        self.description = description

        return self


def get_obj(exception: typing.Union[BaseError, typing.Type[BaseError]]) -> BaseError:
    if isinstance(exception, type):
        return exception()  # type: ignore

    return exception


def combine(*exceptions: BaseError | typing.Type[BaseError]) -> dict[int | str, dict[str, typing.Any]]:
    return {
        status_code: content
        for exception in exceptions
        for status_code, content in get_obj(exception).as_openapi.items()
    }


@_dataclass
class InvalidParametersError(BaseError):
    status_code: int = status.HTTP_400_BAD_REQUEST
    description: str = "Invalid parameters"


@_dataclass
class InvalidLayerError(BaseError):
    status_code: int = status.HTTP_400_BAD_REQUEST
    description: str = "Invalid layer"


@_dataclass
class ConcurrentRequestsError(BaseError):
    status_code: int = status.HTTP_429_TOO_MANY_REQUESTS
    description: str = "Too many concurrent requests"


@_dataclass
class InternalError(BaseError):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    description: str = "Internal server error"
