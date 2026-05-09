from __future__ import annotations

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import NotFoundError
from app.routes import router


async def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AgentReady", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.add_exception_handler(NotFoundError, not_found_handler)
    return app


app = create_app()
