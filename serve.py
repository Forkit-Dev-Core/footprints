"""Serve the Footprints UI alongside the local Forkit Core API."""

import argparse
from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse
from forkit.server import ServerSettings, create_app
from starlette.middleware.trustedhost import TrustedHostMiddleware


def create_footprints_app(registry_root: Path):
    app = create_app(ServerSettings(registry_root=registry_root))
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    ui_root = Path(__file__).resolve().parent

    @app.get("/footprints/", include_in_schema=False)
    def footprints_index():
        return FileResponse(ui_root / "index.html")

    @app.get("/footprints/discovery.js", include_in_schema=False)
    def discovery_script():
        return FileResponse(ui_root / "discovery.js", media_type="text/javascript")

    @app.get("/footprints/passport.js", include_in_schema=False)
    def passport_script():
        return FileResponse(ui_root / "passport.js", media_type="text/javascript")

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--registry-root", type=Path, default=Path.home() / ".forkit" / "footprints"
    )
    options = parser.parse_args()
    uvicorn.run(
        create_footprints_app(options.registry_root.expanduser().resolve()),
        host="127.0.0.1",
        port=options.port,
    )


if __name__ == "__main__":
    main()
