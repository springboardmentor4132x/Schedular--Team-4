"""
App entrypoint. Run with:
    uvicorn app.main:app --reload

This just creates the FastAPI app and plugs in our routers.
As more modules get built (by teammates or by you later), their routers
get included here the same way.
"""

from fastapi import FastAPI

from app.config.settings import settings
from app.routers import auth_router, user_router

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(auth_router.router)
app.include_router(user_router.router)


@app.get("/")
def root():
    return {"message": "SocialPilot Auth Service is running"}
