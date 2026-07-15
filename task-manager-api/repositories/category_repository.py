"""Category persistence (F-012)."""
from sqlalchemy import func, select

from database import db
from models.category import Category


class CategoryRepository:
    def get(self, category_id):
        return db.session.get(Category, category_id)

    def all(self):
        return db.session.execute(select(Category).order_by(Category.id)).scalars().all()

    def total(self):
        return db.session.execute(select(func.count()).select_from(Category)).scalar_one()

    def add(self, category):
        db.session.add(category)
        return category

    def delete(self, category):
        db.session.delete(category)
