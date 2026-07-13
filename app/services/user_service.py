from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password


class UserService:

    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str):
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create_user(db: Session, user: UserCreate):
        hashed_password = hash_password(user.password)

        db_user = User(
            full_name=user.full_name,
            username=user.username,
            email=user.email,
            password=hashed_password,
            phone=user.phone
        )

        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user

        except SQLAlchemyError as e:
            db.rollback()
            print("DATABASE ERROR:", e)
            raise

    @staticmethod
    def update_user(db: Session, db_user: User, user: UserUpdate):

        if user.full_name is not None:
            db_user.full_name = user.full_name

        if user.username is not None:
            db_user.username = user.username

        if user.phone is not None:
            db_user.phone = user.phone

        if user.profile_picture is not None:
            db_user.profile_picture = user.profile_picture

        db.commit()
        db.refresh(db_user)

        return db_user
    
    @staticmethod
    def authenticate_user(db, email: str, password: str):
        from app.utils.security import verify_password
        user = UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password):
            return None
        return user
    

    