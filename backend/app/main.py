from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health", tags=["Ulgam"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Flutter web build bar bolsa, şol bir serwerden berilýär (API we UI bir salgyda).
if settings.static_dir and Path(settings.static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
