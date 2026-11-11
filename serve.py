"""Serve the Footprints UI alongside the local Forkit Core API."""

import argparse
import re
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from forkit.server import ServerSettings, create_app
from starlette.middleware.trustedhost import TrustedHostMiddleware


UI_PATHS = {"/footprints/", "/footprints/passport.js", "/footprints/styles.css", "/readyz"}


async def restrict_core_requests(request: Request, call_next):
    path = request.url.path
    if request.method == "GET" and (
        path in UI_PATHS or re.fullmatch(r"/passports/[0-9a-f]{64}", path)
    ):
        return await call_next(request)

    if request.method != "POST" or (
        path != "/models" and not re.fullmatch(r"/verify/[0-9a-f]{64}", path)
    ):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    origin = request.headers.get("origin")
    if origin is not None and origin != f"{request.url.scheme}://{request.url.netloc}":
        return JSONResponse({"detail": "Use the local Footprints page"}, status_code=403)

    if path == "/models":
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return JSONResponse({"detail": "Expected a JSON model record"}, status_code=415)
        try:
            payload = await request.json()
        except ValueError:
            return JSONResponse({"detail": "Invalid JSON model record"}, status_code=400)
        if not isinstance(payload, dict) or "id" in payload:
            return JSONResponse({"detail": "Core assigns the passport ID"}, status_code=422)

    return await call_next(request)


def create_footprints_app(registry_root: Path):
    app = create_app(ServerSettings(registry_root=registry_root))
    app.middleware("http")(restrict_core_requests)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    ui_root = Path(__file__).resolve().parent

    @app.get("/footprints/", include_in_schema=False)
    def footprints_index():
        return FileResponse(ui_root / "index.html", headers={"X-Frame-Options": "DENY"})

    @app.get("/footprints/passport.js", include_in_schema=False)
    def passport_script():
        return FileResponse(ui_root / "passport.js", media_type="text/javascript")

    @app.get("/footprints/styles.css", include_in_schema=False)
    def footprints_styles():
        return FileResponse(ui_root / "styles.css", media_type="text/css")

    return app


class BrowserServer(uvicorn.Server):
    """Open the workspace only after the local server starts listening."""

    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        if not self.started:
            return
        port = self.config.port or self.servers[0].sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}/footprints/"
        try:
            opened = webbrowser.open(url)
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            print(f"Open {url} in your browser.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open-browser", action="store_true", help="Open Footprints after startup.")
    parser.add_argument(
        "--registry-root", type=Path, default=Path.home() / ".forkit" / "footprints"
    )
    options = parser.parse_args()
    config = uvicorn.Config(
        create_footprints_app(options.registry_root.expanduser().resolve()),
        host="127.0.0.1",
        port=options.port,
    )
    server = BrowserServer(config) if options.open_browser else uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
