from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine as create_db_engine
from telethon.tl.tlobject import TLObject

import typing

from src import db, utils, exceptions, constants
from src.global_variables import GlobalVariables
from src.config import config


def _find_tlobject_by_name(tlobjects: dict[int, TLObject], name: str) -> TLObject:
    for tlobject in tlobjects.values():
        if tlobject.__name__ == name:  # type: ignore
            return tlobject

    raise ValueError(f"TLObject with name {name} not found in layer")

for layer_dirpath in constants.LAYERS_DIRPATH.iterdir():
    if not layer_dirpath.name.isdigit():
        continue

    layer = int(layer_dirpath.name)

    GlobalVariables.layers_tlobjects[layer] = __import__(f"layers.{layer_dirpath.name}.tl.alltlobjects", fromlist=['tlobjects']).tlobjects
    GlobalVariables.layers_coreobjects[layer] = __import__(f"layers.{layer_dirpath.name}.tl.core", fromlist=['core_objects']).core_objects

NEEDED_LAYERS_TLOBJECTS: dict[int, dict[str, TLObject]] = {
    layer: {
        tlobject_name: _find_tlobject_by_name(utils.combine_dicts(tlobjects, GlobalVariables.layers_coreobjects[layer]), tlobject_name)
        for tlobject_name in constants.NEEDED_LAYERS_TLOBJECT_NAMES
    }
    for layer, tlobjects in GlobalVariables.layers_tlobjects.items()
}

GlobalVariables.needed_layers_tlobjects_constructor_ids = {
    layer: {
        tlobject_name: typing.cast(int, tlobject.CONSTRUCTOR_ID)
        for tlobject_name, tlobject in tlobjects.items()
    }
    for layer, tlobjects in NEEDED_LAYERS_TLOBJECTS.items()
}


if not GlobalVariables.layers_tlobjects:
    raise RuntimeError(f"No layers found. Please check the {constants.LAYERS_DIRPATH.resolve().as_posix()} directory.")


from .api import api_router  # noqa


logger = utils.get_logger(
    name = config.logger_name,
    filepath = constants.LOGS_DIRPATH / constants.LOG_FILENAME
)

GlobalVariables.logger = logger


db_engine = create_db_engine(
    url = config.db_url,
    echo = True
)

db_sessionmaker = db.DBSessionMaker(
    bind = db_engine,
    expire_on_commit = False,
    autoflush = False
)

GlobalVariables.db_sessionmaker = db_sessionmaker


web_app = FastAPI(
    title = "Telegram Archiver {}API".format(
        "Test "
        if config.debug
        else
        ""
    ),
    version = constants.APP_VERSION,
    openapi_url = (
        "/openapi.json"
        if config.debug
        else
        None
    ),
    debug = config.debug
)


web_app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)


@web_app.exception_handler(exceptions.BaseError)
async def custom_exceptions_handler(request: Request, ex: exceptions.BaseError | typing.Type[exceptions.BaseError]) -> JSONResponse:
    ex = exceptions.get_obj(ex)

    additional_response: dict[str, typing.Any]

    try:
        additional_response = ex.args[0]
    except Exception:
        additional_response = {}

    return JSONResponse(
        content = ex.as_content,
        status_code = ex.status_code,
        **additional_response
    )


@web_app.exception_handler(HTTPException)
async def http_exceptions_handler(request: Request, ex: HTTPException) -> JSONResponse:
    return JSONResponse(
        content = dict(
            ok = False,
            status_code = ex.status_code,
            description = ex.detail
        ),
        status_code = ex.status_code
    )


@web_app.exception_handler(Exception)
async def handle_all_exceptions(request: Request, ex: Exception) -> JSONResponse:
    GlobalVariables.logger.exception(
        msg = "backend error",
        exc_info = ex
    )

    return await custom_exceptions_handler(
        request = request,
        ex = exceptions.InternalError
    )


# if config.debug:
if True:
    from fastapi.responses import RedirectResponse

    @web_app.get("/", include_in_schema=False)
    async def index_handler() -> RedirectResponse:
        return RedirectResponse(
            url = "/docs",
            status_code = status.HTTP_302_FOUND
        )


web_app.include_router(api_router)


openapi_schema = web_app.openapi()

for schema in openapi_schema.get("components", {}).get("schemas", {}).values():
    if schema.get("additionalProperties"):
        schema["additionalProperties"] = False
