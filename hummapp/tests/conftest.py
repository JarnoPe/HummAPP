import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Lisätään hummapp-kansio sys.pathiin moduulihakuja varten
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User, Horse, NfcTag
from app.auth import get_password_hash, create_access_token

TEST_DATABASE_URL = "sqlite:////tmp/hummapp_test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_directories():
    os.makedirs("/tmp/hummapp_test_videos", exist_ok=True)
    os.makedirs("/tmp/hummapp_test_camera", exist_ok=True)


@pytest.fixture(scope="function")
def db_session():
    # Luodaan puhtaat taulut jokaiseen testiin
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # Alustetaan testi-admin
    admin = User(
        username="admin",
        password_hash=get_password_hash("testpass123"),
        role="admin",
        active=True,
    )
    session.add(admin)

    # Alustetaan Antero
    antero = Horse(name="Antero", active=True)
    session.add(antero)
    session.commit()
    session.refresh(antero)

    # Alustetaan Anterolle tunnettu NFC-tagi
    tag = NfcTag(horse_id=antero.id, nfc_uid="04A31B92C56F80", active=True)
    session.add(tag)
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token():
    return create_access_token({"sub": "admin", "role": "admin", "uid": 1})


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
