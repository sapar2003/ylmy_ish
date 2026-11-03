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


@app.middleware("http")
async def no_stale_ui(request, call_next):
    """Brauzer köne UI faýllaryny ýatda saklamasyn: täze wersiýa goýlanda sahypa täzelenende görünýär
    (ETag bilen barlanýar, üýtgemedik faýl gaýtadan ýüklenmeýär)."""
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


@app.get("/health", tags=["Ulgam"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Flutter web build bar bolsa, şol bir serwerden berilýär (API we UI bir salgyda).
# Mugallym app-ynyň web görnüşi (telefonda brauzerden açmak üçin): /m/
if settings.mobile_dir and Path(settings.mobile_dir).is_dir():
    app.mount("/m", StaticFiles(directory=settings.mobile_dir, html=True), name="mobile")

if settings.static_dir and Path(settings.static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="ui")
