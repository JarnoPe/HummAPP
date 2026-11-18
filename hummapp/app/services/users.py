"""
Käyttäjähallinta. Tunnuksia luo vain ylläpitäjä web-käyttöliittymästä;
rekisteröitymistä tai julkista käyttäjärajapintaa ei ole.
"""
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from app.auth import get_password_hash, verify_password
from app.constants import Role
from app.models import User, utc_now

USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MIN_PASSWORD_LENGTH = 10
ROLE_CHOICES = [Role.USER.value, Role.VIEWER.value, Role.ADMIN.value]


class UserError(ValueError):
    """Käyttäjälle näytettävä virhe. `code` vastaa web/ui.py:n FLASH_MESSAGES-avainta."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def list_users(db: Session) -> List[User]:
    return db.query(User).order_by(User.active.desc(), User.username.asc()).all()


def _validate_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise UserError("salasana-lyhyt")


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == Role.ADMIN.value, User.active == True).count()  # noqa: E712


def create_user(db: Session, username: str, password: str, role: str, display_name: Optional[str] = None) -> User:
    username = (username or "").strip().lower()
    if not USERNAME_RE.match(username):
        raise UserError("tunnus-virheellinen")
    if role not in ROLE_CHOICES:
        raise UserError("rooli-virheellinen")
    _validate_password(password)
    if db.query(User).filter(User.username == username).first():
        raise UserError("tunnus-varattu")
    user = User(
        username=username,
        password_hash=get_password_hash(password),
        role=role,
        active=True,
        display_name=(display_name or "").strip() or None,
        token_version=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, user: User, new_password: str) -> None:
    """Vaihtaa salasanan ja kirjaa käyttäjän ulos kaikilta muilta laitteilta."""
    _validate_password(new_password)
    user.password_hash = get_password_hash(new_password)
    user.token_version = (user.token_version or 0) + 1
    db.commit()


def change_own_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password or "", user.password_hash):
        raise UserError("salasana-vaara")
    set_password(db, user, new_password)


def set_active(db: Session, actor: User, user: User, active: bool) -> None:
    if user.id == actor.id and not active:
        raise UserError("oma-tili")
    if not active and user.role == Role.ADMIN.value and user.active and _active_admin_count(db) <= 1:
        raise UserError("viimeinen-yllapitaja")
    user.active = active
    if not active:
        user.token_version = (user.token_version or 0) + 1  # kirjautumiset päättyvät heti
    db.commit()


def set_role(db: Session, actor: User, user: User, role: str) -> None:
    if role not in ROLE_CHOICES:
        raise UserError("rooli-virheellinen")
    if user.id == actor.id and role != Role.ADMIN.value:
        raise UserError("oma-tili")
    if user.role == Role.ADMIN.value and role != Role.ADMIN.value and user.active and _active_admin_count(db) <= 1:
        raise UserError("viimeinen-yllapitaja")
    if user.role != role:
        user.role = role
        user.token_version = (user.token_version or 0) + 1  # uusi rooli voimaan heti
        db.commit()


def record_login(db: Session, user: User) -> None:
    user.last_login_at = utc_now()
    db.commit()
