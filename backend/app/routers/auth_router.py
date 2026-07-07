"""
Auth endpoints.

POST /api/auth/register  -> creates a new user, returns the user (no password)
POST /api/auth/login     -> verifies credentials, returns a JWT access token

Note: /login uses OAuth2PasswordRequestForm, which is the FastAPI-standard
way to accept 'username' + 'password' as form data. We map our 'email'
field to that 'username' field, since that's what Postman/Swagger UI
and future frontend OAuth2 flows expect.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserCreate, UserResponse, Token
from app.services.user_service import create_user, authenticate_user
from app.auth.security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    new_user = create_user(db, user_in)
    return new_user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return Token(access_token=access_token)
