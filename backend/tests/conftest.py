import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session
from app.db.base import Base
from app.main import app


@pytest.fixture
def client():
    engine = db_session.make_engine("sqlite://")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        with TestSession() as db:
            yield db

    app.dependency_overrides[db_session.get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
