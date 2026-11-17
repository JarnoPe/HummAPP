import datetime
import logging
from typing import List, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.constants import Role
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)

COOKIE_NAME = "access_token"
VIDEO_TOKEN_SCOPE = "video-download"


# --- Salasanat ---------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except ValueError as e:
        logger.error("Salasanan tarkistusvirhe: %s", e)
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    """Palauttaa käyttäjän, jos tunnus ja salasana täsmäävät (aktiivisuus tarkistetaan erikseen)."""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


# --- Tokenit -----------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + (
        expires_delta or datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({**data, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_user_token(user: User) -> str:
    return create_access_token({"sub": user.username, "role": user.role, "uid": user.id})


def create_video_link_token(clip_id: int) -> str:
    """Lyhytikäinen, yhteen leikkeeseen rajattu token ulkoista videosoitinta varten."""
    return create_access_token(
        {"scope": VIDEO_TOKEN_SCOPE, "clip": clip_id},
        datetime.timedelta(minutes=settings.VIDEO_LINK_EXPIRE_MINUTES),
    )


def verify_video_link_token(token: str, clip_id: int) -> bool:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return False
    return payload.get("scope") == VIDEO_TOKEN_SCOPE and payload.get("clip") == clip_id


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.cookie_max_age_seconds,
    )


def get_token_from_request(request: Request, bearer_token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """Token Authorization-headerista (Android) tai HTTP-only evästeestä (web-UI)."""
    if bearer_token:
        return bearer_token
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token.removeprefix("Bearer ")
    return None


def user_from_token(token: Optional[str], db: Session) -> Optional[User]:
    """Yhteinen JWT-tarkistus API:lle ja web-UI:lle. Videolinkkitokenit eivät kelpaa istunnoksi."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    username = payload.get("sub")
    if not username or payload.get("scope"):
        return None
    return db.query(User).filter(User.username == username, User.active == True).first()  # noqa: E712


def get_current_user(token: Optional[str] = Depends(get_token_from_request), db: Session = Depends(get_db)) -> User:
    user = user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kirjautumistieto puuttuu tai se on vanhentunut",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(allowed_roles: List[str]):
    """Tarkistaa käyttäjän roolin (esim. EDITOR_ROLES tai ADMIN_ROLES)."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Toiminto vaatii jonkin seuraavista rooleista: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker


def seed_admin_user(db: Session) -> None:
    """Luo pääkäyttäjän .env-tiedoston ADMIN_USERNAME/ADMIN_PASSWORD-arvoilla, jos sitä ei ole."""
    if db.query(User).filter(User.username == settings.ADMIN_USERNAME).first():
        return
    logger.info("Luodaan pääkäyttäjä '%s'...", settings.ADMIN_USERNAME)
    db.add(
        User(
            username=settings.ADMIN_USERNAME,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            role=Role.ADMIN.value,
            active=True,
        )
    )
    db.commit()
