from fastapi import Depends

import typing

from src import db
from src.global_variables import GlobalVariables


T = typing.TypeVar("T")


async def _get_db_session() -> typing.AsyncIterator[db.DBSession]:
    async with GlobalVariables.db_sessionmaker() as db_session:
        try:
            yield db_session

        except Exception:
            await db_session.rollback()
            raise

        finally:
            await db_session.close()

get_db_session = Depends(_get_db_session)
