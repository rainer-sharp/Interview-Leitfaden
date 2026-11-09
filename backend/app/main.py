from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.catalogs import router as catalogs_router
from app.config import get_settings, validate_secrets

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_secrets(get_settings())
    yield


# Swagger/ReDoc bleiben aus: sie laden Skripte von externen CDNs (SPEC: keine externen CDNs).
app = FastAPI(title="Interview-Leitfaden", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(catalogs_router, prefix="/api")

if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str) -> FileResponse:
    """Liefert die Vue-App aus; das Routing übernimmt der Browser."""
    index = STATIC_DIR / "index.html"
    if path.startswith("api/") or not index.exists():
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
