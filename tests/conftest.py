import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.patient import Patient  # noqa: F401
from app.models.registration import Registration  # noqa: F401


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def client(db_factory, monkeypatch):
    monkeypatch.setattr(settings, "vapi_webhook_secret", "test-webhook-secret")
    monkeypatch.setattr(settings, "api_key", "")

    def override():
        with db_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def patient():
    return {
        "first_name": "Jane",
        "last_name": "Demo",
        "date_of_birth": "06/14/1993",
        "sex": "Female",
        "phone_number": "+1 (415) 555-0182",
        "address_line_1": "123 Fictional Street",
        "city": "San Francisco",
        "state": "ca",
        "zip_code": "94105",
    }
