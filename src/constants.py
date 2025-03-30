from pathlib import Path


ENCODING = "utf-8"

APP_VERSION = "0.1.0"


PARENT_DIRPATH = Path(__file__).parent.parent
LOGS_DIRPATH = PARENT_DIRPATH / "logs"
LAYERS_DIRPATH = PARENT_DIRPATH / "layers"

LOG_FILENAME = "log.txt"


if not LOGS_DIRPATH.exists():
    LOGS_DIRPATH.mkdir()
