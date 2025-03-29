from pydantic import BaseModel, ConfigDict, Field


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


__all__ = (
    "BaseResponse",
    "BaseRequest",
    "BaseCustomizableModel",
)
