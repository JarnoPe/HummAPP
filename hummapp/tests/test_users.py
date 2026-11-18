"""Käyttäjähallinta: vain ylläpitäjä luo tunnukset, roolit rajaavat muutokset, istunnot mitätöityvät."""
import pytest

from app.auth import create_user_token
from app.models import User


def login_cookie(client, token):
    client.cookies.set("access_token", f"Bearer {token}")


@pytest.fixture
def admin_client(client, admin_token):
    login_cookie(client, admin_token)
    return client


def create(client, username="maija", password="hevonen-2026x", role="user", name="Maija"):
    return client.post("/web/users/create", data={"username": username, "password": password, "role": role,
                                                  "display_name": name}, follow_redirects=False)


def test_no_public_registration(client):
    for path in ("/api/register", "/api/users", "/web/register"):
        assert client.post(path, json={"username": "x", "password": "y" * 12}).status_code in (401, 404, 405)


def test_admin_creates_user_who_can_log_in(admin_client, db_session):
    r = create(admin_client)
    assert "ilmoitus=kayttaja-luotu" in r.headers["location"]
    admin_client.cookies.clear()
    r = admin_client.post("/api/login", json={"username": "maija", "password": "hevonen-2026x"})
    assert r.status_code == 200 and r.json()["role"] == "user"
    assert db_session.query(User).filter_by(username="maija").one().last_login_at is not None


@pytest.mark.parametrize("username,password,code", [
    ("Ma", "hevonen-2026x", "tunnus-virheellinen"),
    ("mäijä", "hevonen-2026x", "tunnus-virheellinen"),
    ("maija", "lyhyt", "salasana-lyhyt"),
])
def test_create_user_validation(admin_client, username, password, code):
    assert f"ilmoitus={code}" in create(admin_client, username, password).headers["location"]


def test_duplicate_username(admin_client):
    create(admin_client)
    assert "ilmoitus=tunnus-varattu" in create(admin_client).headers["location"]


def test_non_admin_cannot_manage_users(client, db_session, admin_client):
    create(admin_client, role="user")
    user = db_session.query(User).filter_by(username="maija").one()
    client.cookies.clear()
    login_cookie(client, create_user_token(user))
    assert client.get("/web/users").status_code == 403
    assert create(client, username="hakkeri").status_code == 403


def test_viewer_cannot_modify(client, db_session, admin_client):
    create(admin_client, username="katsoja", role="viewer")
    viewer = db_session.query(User).filter_by(username="katsoja").one()
    client.cookies.clear()
    login_cookie(client, create_user_token(viewer))
    assert client.get("/web/horses").status_code == 200
    assert "Yhdistä tagi" not in client.get("/web/horses").text
    assert client.post("/web/horses/create", data={"name": "Uusi"}, follow_redirects=False).status_code == 403
    assert client.post("/web/water/sync", follow_redirects=False).status_code == 403


def test_deactivation_ends_sessions_immediately(client, db_session, admin_client):
    create(admin_client)
    user = db_session.query(User).filter_by(username="maija").one()
    token = create_user_token(user)
    r = admin_client.post(f"/web/users/{user.id}/active", data={"active": "0"}, follow_redirects=False)
    assert "kayttaja-passivoitu" in r.headers["location"]
    admin_client.cookies.clear()
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/api/login", json={"username": "maija", "password": "hevonen-2026x"}).status_code == 403


def test_password_reset_invalidates_old_tokens(client, db_session, admin_client):
    create(admin_client)
    user = db_session.query(User).filter_by(username="maija").one()
    old = create_user_token(user)
    admin_client.post(f"/web/users/{user.id}/password", data={"password": "uusi-salasana-99"})
    admin_client.cookies.clear()
    assert client.get("/api/me", headers={"Authorization": f"Bearer {old}"}).status_code == 401
    assert client.post("/api/login", json={"username": "maija", "password": "uusi-salasana-99"}).status_code == 200


def test_admin_cannot_lock_themselves_out(admin_client, db_session):
    admin = db_session.query(User).filter_by(username="admin").one()
    r = admin_client.post(f"/web/users/{admin.id}/active", data={"active": "0"}, follow_redirects=False)
    assert "ilmoitus=oma-tili" in r.headers["location"]
    r = admin_client.post(f"/web/users/{admin.id}/role", data={"role": "user"}, follow_redirects=False)
    assert "ilmoitus=oma-tili" in r.headers["location"]
    db_session.refresh(admin)
    assert admin.active and admin.role == "admin"


def test_own_password_change_keeps_current_session(admin_client):
    r = admin_client.post("/web/account/password", data={
        "current_password": "testpass123", "new_password": "uusi-pitka-salasana", "new_password_again": "uusi-pitka-salasana",
    }, follow_redirects=False)
    assert "oma-salasana-vaihdettu" in r.headers["location"]
    new_cookie = r.cookies.get("access_token") or r.headers.get("set-cookie", "")
    assert new_cookie
    assert admin_client.get("/web/account").status_code == 200


def test_own_password_wrong_current(admin_client):
    r = admin_client.post("/web/account/password", data={
        "current_password": "vaara", "new_password": "uusi-pitka-salasana", "new_password_again": "uusi-pitka-salasana",
    }, follow_redirects=False)
    assert "salasana-vaara" in r.headers["location"]


def test_users_page_renders(admin_client):
    create(admin_client)
    text = admin_client.get("/web/users").text
    assert "Maija" in text and "Tallin käyttäjä" in text
