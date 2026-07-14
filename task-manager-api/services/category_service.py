"""Category use cases (F-005, F-016)."""
from database import db
from errors import NotFoundError, ValidationError
from models.category import Category
from repositories.category_repository import CategoryRepository
from repositories.task_repository import TaskRepository
from validators import DEFAULT_COLOR


class CategoryService:
    def __init__(self, categories=None, tasks=None):
        self.categories = categories or CategoryRepository()
        self.tasks = tasks or TaskRepository()

    def get_required(self, category_id):
        category = self.categories.get(category_id)
        if not category:
            raise NotFoundError('Categoria não encontrada')
        return category

    def list_with_counts(self):
        categories = self.categories.all()
        counts = self.tasks.category_counts()
        return [(category, counts.get(category.id, 0)) for category in categories]

    def create(self, data):
        name = data.get('name')
        if not name or not isinstance(name, str) or not name.strip():
            raise ValidationError('Nome é obrigatório')

        category = Category()
        category.name = name.strip()
        category.description = data.get('description', '')
        category.color = data.get('color', DEFAULT_COLOR)

        self.categories.add(category)
        db.session.commit()
        return category

    def update(self, category_id, data):
        category = self.get_required(category_id)

        if 'name' in data:
            if not data['name'] or not isinstance(data['name'], str) or not data['name'].strip():
                raise ValidationError('Nome é obrigatório')
            category.name = data['name'].strip()
        if 'description' in data:
            category.description = data['description']
        if 'color' in data:
            category.color = data['color']

        db.session.commit()
        return category

    def delete(self, category_id):
        category = self.get_required(category_id)
        self.categories.delete(category)
        db.session.commit()
