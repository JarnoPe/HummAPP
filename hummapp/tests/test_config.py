import pytest
from pydantic import ValidationError

from app.config import Settings


def test_example_secret_rejected():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="vaihda-tama-salaisuus-openssl-rand-hex-32-arvolla-tuotantoon", ADMIN_PASSWORD="x" * 16)


def test_known_default_password_rejected():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="a" * 64, ADMIN_PASSWORD="Tallipaallikko2026!")


def test_missing_secrets_rejected(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
