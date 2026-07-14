"""Task persistence (F-008, F-010, F-012).

Owns query construction and eager loading. Uses SQLAlchemy 2.0 `session.get()`
and `select()` instead of the legacy `Model.query` API deprecated in 2.0.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from database import db
from models.task import Task


class TaskRepository:
    def get(self, task_id):
        return db.session.get(Task, task_id)

    def get_with_relations(self, task_id):
        stmt = (
            select(Task)
            .options(selectinload(Task.user), selectinload(Task.category))
            .where(Task.id == task_id)
        )
        return db.session.execute(stmt).scalar_one_or_none()

    def _base_query(self, query=None, status=None, priority=None, user_id=None):
        stmt = select(Task).options(selectinload(Task.user), selectinload(Task.category))
        if query:
            like = f'%{query}%'
            stmt = stmt.where(or_(Task.title.like(like), Task.description.like(like)))
        if status:
            stmt = stmt.where(Task.status == status)
        if priority is not None:
            stmt = stmt.where(Task.priority == priority)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)
        return stmt

    def paginate(self, page, per_page, **filters):
        """Bounded read with relations eager-loaded: 3 queries regardless of row count."""
        stmt = self._base_query(**filters).order_by(Task.id)
        total = db.session.execute(
            select(func.count()).select_from(self._base_query(**filters).subquery())
        ).scalar_one()
        rows = db.session.execute(stmt.limit(per_page).offset((page - 1) * per_page)).scalars().all()
        return rows, total

    def list_for_user(self, user_id, page, per_page):
        return self.paginate(page, per_page, user_id=user_id)

    def status_counts(self):
        """One grouped query replacing five separate count() round-trips."""
        rows = db.session.execute(select(Task.status, func.count()).group_by(Task.status)).all()
        return {status: count for status, count in rows}

    def priority_counts(self):
        rows = db.session.execute(select(Task.priority, func.count()).group_by(Task.priority)).all()
        return {priority: count for priority, count in rows}

    def total(self):
        return db.session.execute(select(func.count()).select_from(Task)).scalar_one()

    def count_for_category(self, category_id):
        return db.session.execute(
            select(func.count()).select_from(Task).where(Task.category_id == category_id)
        ).scalar_one()

    def category_counts(self):
        rows = db.session.execute(
            select(Task.category_id, func.count()).group_by(Task.category_id)
        ).all()
        return {category_id: count for category_id, count in rows}

    def all_with_due_date(self):
        """Only rows that can possibly be overdue, instead of the whole table."""
        stmt = select(Task).where(Task.due_date.is_not(None))
        return db.session.execute(stmt).scalars().all()

    def list_for_user_ids(self):
        """(user_id, status, count) aggregate powering the productivity report."""
        rows = db.session.execute(
            select(Task.user_id, Task.status, func.count()).group_by(Task.user_id, Task.status)
        ).all()
        return rows

    def created_since(self, since):
        return db.session.execute(
            select(func.count()).select_from(Task).where(Task.created_at >= since)
        ).scalar_one()

    def completed_since(self, since):
        return db.session.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.status == 'done', Task.updated_at >= since)
        ).scalar_one()

    def list_for_user_all(self, user_id):
        stmt = select(Task).where(Task.user_id == user_id)
        return db.session.execute(stmt).scalars().all()

    def add(self, task):
        db.session.add(task)
        return task

    def delete(self, task):
        db.session.delete(task)
