from uvicorn import run as run_uvicorn

from src.config import config


if not config.debug:
    raise RuntimeError("To run as \"python -m src\" it must be run in debug mode only")


run_uvicorn(
    app = "src:web_app",
    host = config.host,
    port = config.port,
    loop = "none",
    access_log = config.debug,
    use_colors = True,
    server_header = False,
    reload = config.debug
)
