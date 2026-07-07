"""
Database connection setup.

- engine: the actual connection to PostgreSQL
- SessionLocal: creates a new DB session per request
- Base: parent class every model (table) inherits from
- get_db: FastAPI dependency that gives each request its own DB session
  and always closes it afterward (even if an error happens)
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.settings import settings

engine = create_engine(settings.DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
