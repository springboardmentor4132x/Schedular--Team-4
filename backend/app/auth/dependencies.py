"""
This is the gatekeeper dependency. Any route that needs a logged-in user
adds `current_user: User = Depends(get_current_user)` as a parameter.

Flow:
1. FastAPI's OAuth2PasswordBearer pulls the "Bearer <token>" from the
   Authorization header.
2. We decode the token. If invalid/expired -> 401.
3. We look up the user in the DB using the email stored in the token.
4. If found and active, we return the User object to the route.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.auth.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user
