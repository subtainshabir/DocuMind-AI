"""
DocuMind AI - FastAPI entry point.

Serves the frontend (via Jinja2 templates + static files) and, as of
Phase 2, the document upload/list/delete API.
"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.routes.documents import router as documents_router

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

templates = Jinja2Templates(directory=TEMPLATES_DIR)

app = FastAPI(title="DocuMind AI", version="0.2.0")

# Serve everything inside /static (css, js, images) at the /static URL.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Phase 2: document upload / list / get / delete endpoints.
app.include_router(documents_router)


@app.get("/")
def serve_frontend(request: Request):
    """
    Root route. Renders the main DocuMind AI page from templates/index.html.
    """
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health_check():
    """
    Simple health/status endpoint.
    Used to confirm the backend is running, useful for future phases
    (deployment checks, uptime monitoring, frontend connectivity tests).
    """
    return {"status": "ok", "service": "DocuMind AI", "phase": 2}