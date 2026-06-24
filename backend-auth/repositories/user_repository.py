from sqlalchemy import or_
from sqlalchemy.orm import Session
from database.models import User, StudentProfile, TeacherProfile, Role
from typing import Optional

class UserRepository:
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_verification_token(db: Session, token: str) -> Optional[User]:
        return db.query(User).filter(User.verification_token == token).first()

    @staticmethod
    def get_by_reset_token(db: Session, token: str) -> Optional[User]:
        return db.query(User).filter(User.reset_token == token).first()

    @staticmethod
    def create_student(db: Session, user_data: dict, profile_data: dict) -> User:
        new_user = User(**user_data)
        db.add(new_user)
        db.flush()
        
        new_profile = StudentProfile(user_id=new_user.id, **profile_data)
        db.add(new_profile)
        
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def create_teacher(db: Session, user_data: dict, profile_data: dict) -> User:
        new_user = User(**user_data)
        db.add(new_user)
        db.flush()
        
        new_profile = TeacherProfile(user_id=new_user.id, **profile_data)
        db.add(new_profile)
        
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def update(db: Session) -> None:
        db.commit()
        
    @staticmethod
    def get_all_filtered(db: Session, role_name: Optional[str] = None, career_id: Optional[int] = None, skip: int = 0, limit: int = 100):
        query = db.query(User)

        if role_name:
            query = query.join(Role).filter(Role.role_name == role_name)

        if career_id:
            query = query.outerjoin(StudentProfile, User.id == StudentProfile.user_id) \
                        .outerjoin(TeacherProfile, User.id == TeacherProfile.user_id) \
                        .filter(
                            or_(
                                StudentProfile.career_id == career_id,
                                TeacherProfile.career_id == career_id
                            )
                        )

        total_count = query.count()
        users = query.offset(skip).limit(limit).all()
        return total_count, users

    @staticmethod
    def delete_user(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()