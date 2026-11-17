from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import authenticate, create_user_token, get_current_user, set_auth_cookie
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserResponse

router = APIRouter(tags=["Autentikointi"])


@router.post("/api/login", response_model=TokenResponse)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Kirjautuminen. Palauttaa JWT-tokenin Android-sovellukselle ja asettaa HTTP-only evästeen selaimelle."""
    user = authenticate(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Virheellinen käyttäjätunnus tai salasana",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Käyttäjätili on passivoitu")

    access_token = create_user_token(user)
    set_auth_cookie(response, access_token)
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
