import pytest

from app.core.config import Settings
from app.validators.patient import dob, name, phone, state, zip_code


@pytest.mark.parametrize(
    "value",
    [
        "415-555-0123",
        "+1 (415) 555.0123",
        "415 555 0123",
        "four one five dash five five five dash zero one two three",
    ],
)
def test_phone_normalization(value):
    assert phone(value) == "4155550123"


def test_validation_functions():
    assert name(" O’Neil ") == "O'Neil"
    assert name("Anne-Marie") == "Anne-Marie"
    assert dob("5/12/1988").isoformat() == "1988-05-12"
    assert state(" pr ") == "PR"
    assert zip_code("12345-6789") == "12345-6789"
    with pytest.raises(ValueError):
        phone("4155550123 extension 1")


def test_production_fails_closed():
    with pytest.raises(ValueError):
        Settings(_env_file=None, app_env="production", database_url="sqlite:///demo.db")
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql://demo/db",
            api_key="",
            vapi_webhook_secret="",
        )
