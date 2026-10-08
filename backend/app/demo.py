"""Host the existing FastAPI API and compiled React frontend on one origin."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from app.main import app as api

class SPAStaticFiles(StaticFiles):
    """Serve index.html for client routes while keeping missing assets as 404."""
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404 and scope["method"] in {"GET", "HEAD"} and "." not in Path(path).name:
                return await super().get_response("index.html", scope)
            raise

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Mounted FastAPI apps do not automatically receive their own startup events.
    async with api.router.lifespan_context(api):
        yield

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount("/api", api)
dist = os.getenv("ATLAS_FRONTEND_DIST", str(Path(__file__).resolve().parents[1] / "frontend-dist"))
app.mount("/", SPAStaticFiles(directory=dist, html=True, check_dir=False), name="frontend")
