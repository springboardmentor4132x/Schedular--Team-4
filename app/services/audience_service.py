from sqlalchemy.orm import Session

from app.models.audience import Audience


class AudienceService:

    @staticmethod
    def create_audience(db: Session, audience):
        db_audience = Audience(**audience.dict())

        db.add(db_audience)
        db.commit()
        db.refresh(db_audience)

        return db_audience

    @staticmethod
    def get_all_audience(db: Session):
        return db.query(Audience).all()

    @staticmethod
    def get_platform_audience(db: Session, platform: str):
        return (
            db.query(Audience)
            .filter(Audience.platform == platform)
            .all()
        )