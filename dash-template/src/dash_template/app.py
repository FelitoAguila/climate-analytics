"""Application factory and entry point."""

from __future__ import annotations

import os

from dash import Dash
from dotenv import load_dotenv

from . import config
from .callbacks import register_callbacks
from .components.shell import shell

load_dotenv()

_ASSETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def create_app() -> Dash:
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
    return app


app = create_app()
server = app.server


def main() -> None:
    app.run(
        debug=os.getenv("DASH_DEBUG", "true").lower() == "true",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
    )


if __name__ == "__main__":
    main()
