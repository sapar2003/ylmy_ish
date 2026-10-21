import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.base import Base
from app.core.config import settings
from app.main import app

client_session_factory = []  # test maglumatlaryny göni ýazmak üçin (meselem, seed)


@pytest.fixture
def client():
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
    settings.generation_in_background = False
    client_session_factory.append(TestSession)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    client_session_factory.clear()
    engine.dispose()
