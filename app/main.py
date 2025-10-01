from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.routes import health, merge, ui
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Internal PDF Merger", version="1.0.0")
    if settings.use_proxy_headers:
        trusted_hosts = list(settings.proxy_trusted_hosts) or None
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_hosts)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/merge":
            content_length = request.headers.get("content-length")
            if content_length and content_length.isdigit():
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > settings.max_total_upload_mb:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Payload too large (> {settings.max_total_upload_mb} MB)."
                        },
                    )
        return await call_next(request)

    app.include_router(ui.router)
    app.include_router(merge.router)
    app.include_router(health.router)

    return app


app = create_app()
