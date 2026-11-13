import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import TokenResponse, LoginRequest, UserResponse
from app.auth import verify_password, create_access_token, get_current_user

router = APIRouter(tags=["Autentikointi"])


@router.post("/api/login", response_model=TokenResponse)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Kirjautuminen käyttäjätunnuksella ja salasanalla.
    Palauttaa JWT-tokenin Android-sovellukselle ja asettaa tarvittaessa
    HTTP-only evästeen selaimelle.
    """
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Virheellinen käyttäjätunnus tai salasana",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Käyttäjätili on passivoitu",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role, "uid": user.id})

    # Aseta eväste verkkoselaimen web-käyttöliittymää varten
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        user_id=user.id,
    )


@router.get("/api/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Palauttaa kirjautuneen käyttäjän omat tiedot."""
    return current_user
