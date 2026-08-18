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

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(documents_router)


@app.get("/")
def serve_frontend(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "DocuMind AI", "phase": 2}