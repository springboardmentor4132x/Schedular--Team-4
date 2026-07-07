"""
Central configuration for the app.
Every setting is loaded from environment variables (.env file).
Why: hardcoding DB passwords / secret keys in code is a security risk
and makes it impossible to have different settings for dev/staging/prod.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SocialPilot Auth Service"

    # Database
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"


# Single shared instance imported everywhere else in the app
settings = Settings()
