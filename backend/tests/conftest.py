import os
import tempfile
from pathlib import Path
ROOT = Path(tempfile.mkdtemp(prefix="atlas-tests-"))
os.environ.update(DATABASE_URL=f"sqlite:///{ROOT / 'test.db'}", STORAGE_DIR=str(ROOT / "uploads"), QDRANT_PATH=str(ROOT / "qdrant"), JWT_SECRET="test-secret-never-use-outside-tests-123456789", EMBEDDING_PROVIDER="hash", LLM_PROVIDER="extractive")
import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, engine
from app.main import app
from app.core.rate_limit import _local

@pytest.fixture
def client():
    _local.clear()
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
