"""Application factory and entry point."""

from __future__ import annotations

from pathlib import Path

from dash import Dash

from . import config
from .callbacks import register_callbacks
from .components.shell import shell
from .settings import get_settings

_ASSETS_FOLDER = str(Path(__file__).resolve().parent / "assets")


def create_app() -> Dash:
    get_settings()
    app = Dash(
        __name__,
        title=config.APP_NAME,
        update_title=None,
        suppress_callback_exceptions=True,
        assets_folder=_ASSETS_FOLDER,
        external_stylesheets=config.EXTERNAL_STYLESHEETS,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            {"name": "description", "content": config.APP_DESCRIPTION},
        ],
    )
    app.layout = shell()
    register_callbacks(app)

    @app.server.get("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()
server = app.server


def main() -> None:
    settings = get_settings()
    app.run(debug=settings.dash_debug, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
