from pydantic import BaseModel
from yaml.representer import SafeRepresenter
from typing_extensions import Self

import yaml
import signal
import os
import typing

from src import enums, constants


CONFIG_FILEPATH = constants.PARENT_DIRPATH / (
    (
        "config.test.yml"
        if "TG_ARCHIVE_BACKEND_TEST_CFG" in os.environ
        else
        os.environ["TG_ARCHIVE_BACKEND_CFG"]
    )
    if "TG_ARCHIVE_BACKEND_TEST_CFG" in os.environ or "TG_ARCHIVE_BACKEND_CFG" in os.environ
    else
    "config.yml"
)


yaml.Dumper.add_multi_representer(
    data_type = enums.BaseEnum,
    representer = SafeRepresenter.represent_str
)


class Config(BaseModel):
    debug: bool
    logger_name: str
    logger_file_level: str
    logger_console_level: str
    db_url: str
    host: str
    port: int

    @classmethod
    def load(cls) -> Self:
        with CONFIG_FILEPATH.open("r", encoding=constants.ENCODING) as file:
            return cls.model_validate(
                obj = yaml.load(
                    stream = file,
                    Loader = yaml.Loader
                )
            )

    def save(self) -> None:
        with CONFIG_FILEPATH.open("w", encoding=constants.ENCODING) as file:
            yaml.dump(
                data = self.model_dump(),
                stream = file,
                indent = 2,
                allow_unicode = True,
                sort_keys = False
            )

        os.kill(os.getppid(), signal.SIGUSR1)


config = Config.load()


def _reload_config(*args: typing.Any) -> None:
    global config

    config = config.load()

signal.signal(signal.SIGUSR1, _reload_config)
