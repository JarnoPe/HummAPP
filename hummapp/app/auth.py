import datetime
import logging
from typing import Optional, List
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_token_from_request(request: Request, bearer_token: Optional[str] = Depends(oauth2_scheme)) -> Optional[str]:
    """Hakee tokenin joko Authorization-headerista tai web-käyttöliittymän evästeestä."""
    if bearer_token:
        return bearer_token
    # Tarkista selaimen HTTP-only eväste
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:]
        return cookie_token
    return None


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kirjautumistieto puuttuu tai se on vanhentunut",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username, User.active == True).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(allowed_roles: List[str]):
    """Tarkistaa käyttäjän roolin (esim. ['admin'] tai ['admin', 'user'])."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Toiminto vaatii jonkin seuraavista rooleista: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker


def seed_admin_user(db: Session):
    """Luo oletuspääkäyttäjän, mikäli järjestelmässä ei vielä ole yhtään käyttäjää."""
    admin_user = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
    if not admin_user:
        logger.info(f"Luodaan oletuspääkäyttäjä '{settings.ADMIN_USERNAME}'...")
        hashed_pw = get_password_hash(settings.ADMIN_PASSWORD)
        new_admin = User(
            username=settings.ADMIN_USERNAME,
            password_hash=hashed_pw,
            role="admin",
            active=True,
        )
        db.add(new_admin)
        db.commit()
        logger.info("Oletuspääkäyttäjä luotu onnistuneesti.")
