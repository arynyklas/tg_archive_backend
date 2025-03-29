from src import db, utils


class GlobalVariables:
    logger: utils.logging.Logger
    db_sessionmaker: db.DBSessionMaker
