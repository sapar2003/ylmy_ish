import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.auth import require_admin, require_staff
from app.db import session as db_session
from app.db.base import Base
from app.core.config import settings
from app.main import app

client_session_factory = []  # test maglumatlaryny göni ýazmak üçin (meselem, seed)


def _make_client(as_admin: bool):
    # Adaty: in-memory SQLite. PostgreSQL bilen barlamak üçin TEST_DATABASE_URL beriň.
    engine = db_session.make_engine(os.environ.get("TEST_DATABASE_URL", "sqlite://"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        with TestSession() as db:
            yield db

    app.dependency_overrides[db_session.get_db] = override
    app.dependency_overrides[db_session.get_session_factory] = lambda: TestSession
    if as_admin:  # köp testde giriş barlagy gerek däl: admin hökmünde işleýär
        app.dependency_overrides[require_admin] = lambda: None
        app.dependency_overrides[require_staff] = lambda: None
    settings.generation_in_background = False
    client_session_factory.append(TestSession)
    return engine, TestClient(app)


@pytest.fixture
def client():
    engine, c = _make_client(as_admin=True)
    with c:
        yield c
    app.dependency_overrides.clear()
    client_session_factory.clear()
    engine.dispose()


@pytest.fixture
def anon_client():
    """Giriş barlagy hakyky işleýän müşderi (token bolmasa admin API ýapyk)."""
    engine, c = _make_client(as_admin=False)
    with c:
        yield c
    app.dependency_overrides.clear()
    client_session_factory.clear()
    engine.dispose()
