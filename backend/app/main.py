import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import require_auth, router as auth_router
from app.api.backup import router as backup_router
from app.api.catalogs import router as catalogs_router
from app.api.evaluation import router as evaluation_router
from app.api.imports import router as imports_router
from app.api.interviews import router as interviews_router
from app.api.projects import router as projects_router
from app.api.recordings import router as recordings_router
from app.api.settings import llm_router, router as settings_router
from app.config import get_settings, validate_secrets
from app.services import evaluation
from app.services.transcription import worker

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    validate_secrets(settings)
    if settings.transcription_worker:
        worker.start()
        evaluation.worker.start()
    yield
    worker.stop()
    evaluation.worker.stop()


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
    """version = Git-Stand des Images (Build-Argument GIT_COMMIT); so lässt sich ein Update prüfen."""
    return {"status": "ok", "version": os.environ.get("APP_VERSION", "entwicklung")}


app.include_router(auth_router, prefix="/api")
for protected in (
    projects_router, catalogs_router, imports_router, interviews_router, recordings_router, evaluation_router,
    settings_router, llm_router, backup_router,
):
    app.include_router(protected, prefix="/api", dependencies=[Depends(require_auth)])

if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str) -> FileResponse:
    """Liefert die Vue-App aus; das Routing übernimmt der Browser."""
    index = STATIC_DIR / "index.html"
    if path.startswith("api/") or not index.exists():
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
