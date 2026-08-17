from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Base directory of this project, used to build reliable file paths
BASE_DIR = Path(__file__).resolve().parent
# add near STATIC_DIR
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
STATIC_DIR = BASE_DIR /"static"

app = FastAPI(title="DocuMind AI", version="0.1.0")

# Serve everything inside /static (css, js, images) at the /static URL.

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_frontend(request: Request):
    """
    Root route. Renders the main DocuMind AI page from templates/index.html.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health_check():
    """
    Simple health/status endpoint.
    Used to confirm the backend is running, useful for future phases
    (deployment checks, uptime monitoring, frontend connectivity tests).
    """
    return {"status": "ok", "service": "DocuMind AI", "phase": 1}