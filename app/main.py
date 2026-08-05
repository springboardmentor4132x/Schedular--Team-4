from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine

# Import all models
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.campaign import Campaign
from app.models.post import Post
from app.models.analytics import Analytics
from app.routers import social_account_router

# Import routers
from app.routers import auth_router, campaign_router

from app.routers import post_router

from app.routers import (
    auth_router,
    campaign_router,
    social_account_router,
    post_router,
    analytics_router
)
from app.models.audience import Audience
from app.routers import audience_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    debug=True
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers

app.include_router(auth_router)
app.include_router(campaign_router)
app.include_router(social_account_router)
app.include_router(post_router)
app.include_router(analytics_router)
app.include_router(audience_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to SocialPilot Backend",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.post("/test/handshake")
def handshake():
    return {
        "success": True,
        "message": "Backend connected successfully!"
    }

