from telethon.tl.tlobject import TLObject

from src import db, utils


class GlobalVariables:
    logger: utils.logging.Logger
    db_sessionmaker: db.DBSessionMaker
    layers_tlobjects: dict[int, dict[int, TLObject]] = {}  # {layer: {constructor_id: TLObject}}
    layers_coreobjects: dict[int, dict[int, TLObject]] = {}  # {layer: {constructor_id: TLObject}}
