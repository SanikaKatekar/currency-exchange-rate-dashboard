from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import STATIC_DIR

app = FastAPI(
    title="Currency Exchange Rate Dashboard",
    description="EUR→USD rates with daily breakdown, totals, and a visual dashboard.",
    version="1.0.0",
)

app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(Path(STATIC_DIR) / "index.html")
