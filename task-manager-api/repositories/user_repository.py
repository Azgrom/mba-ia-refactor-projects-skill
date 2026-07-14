"""User persistence (F-008, F-010, F-012)."""
from sqlalchemy import func, select

from database import db
from models.task import Task
from models.user import User


class UserRepository:
    def get(self, user_id):
        return db.session.get(User, user_id)

    def find_by_email(self, email):
        return db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def paginate(self, page, per_page):
        total = db.session.execute(select(func.count()).select_from(User)).scalar_one()
        rows = (
            db.session.execute(
                select(User).order_by(User.id).limit(per_page).offset((page - 1) * per_page)
            )
            .scalars()
            .all()
        )
        return rows, total

    def task_counts(self):
        """One grouped query, replacing a per-user `len(u.tasks)` lazy load."""
        rows = db.session.execute(
            select(Task.user_id, func.count()).group_by(Task.user_id)
        ).all()
        return {user_id: count for user_id, count in rows}

    def total(self):
        return db.session.execute(select(func.count()).select_from(User)).scalar_one()

    def all(self):
        return db.session.execute(select(User).order_by(User.id)).scalars().all()

    def add(self, user):
        db.session.add(user)
        return user

    def delete(self, user):
        db.session.delete(user)
