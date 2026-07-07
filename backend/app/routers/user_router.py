"""
GET /api/users/profile
A protected route: only accessible with a valid JWT (Bearer token).
This proves the full loop works: register -> login -> get token -> use token.
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.schemas.user import UserResponse
from app.models.user import User

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
