"""Task use cases (F-005). Owns orchestration and the transaction boundary."""
from database import db
from errors import NotFoundError, ValidationError
from models.task import Task
from repositories.category_repository import CategoryRepository
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from timeutil import utcnow
from utils.helpers import calculate_percentage
from validators import (
    DEFAULT_PRIORITY,
    parse_due_date,
    parse_priority,
    parse_status,
    parse_tags,
    parse_title,
)


class TaskService:
    def __init__(self, tasks=None, users=None, categories=None):
        self.tasks = tasks or TaskRepository()
        self.users = users or UserRepository()
        self.categories = categories or CategoryRepository()

    def _require_user(self, user_id):
        if user_id is None:
            return None
        if not self.users.get(user_id):
            raise NotFoundError('Usuário não encontrado')
        return user_id

    def _require_category(self, category_id):
        if category_id is None:
            return None
        if not self.categories.get(category_id):
            raise NotFoundError('Categoria não encontrada')
        return category_id

    def get_required(self, task_id):
        task = self.tasks.get_with_relations(task_id)
        if not task:
            raise NotFoundError('Task não encontrada')
        return task

    def list(self, page, per_page, **filters):
        return self.tasks.paginate(page, per_page, **filters)

    def create(self, data):
        if not data.get('title'):
            raise ValidationError('Título é obrigatório')

        task = Task()
        task.title = parse_title(data['title'])
        task.description = data.get('description', '')
        task.status = parse_status(data.get('status', 'pending'))
        task.priority = parse_priority(data.get('priority', DEFAULT_PRIORITY))
        task.user_id = self._require_user(data.get('user_id'))
        task.category_id = self._require_category(data.get('category_id'))
        task.due_date = parse_due_date(data.get('due_date'))
        task.tags = parse_tags(data.get('tags'))

        self.tasks.add(task)
        db.session.commit()
        return self.tasks.get_with_relations(task.id)

    def update(self, task_id, data):
        task = self.get_required(task_id)

        if 'title' in data:
            task.title = parse_title(data['title'])
        if 'description' in data:
            task.description = data['description']
        if 'status' in data:
            task.status = parse_status(data['status'])
        if 'priority' in data:
            task.priority = parse_priority(data['priority'])
        if 'user_id' in data:
            task.user_id = self._require_user(data['user_id'])
        if 'category_id' in data:
            task.category_id = self._require_category(data['category_id'])
        if 'due_date' in data:
            task.due_date = parse_due_date(data['due_date'])
        if 'tags' in data:
            task.tags = parse_tags(data['tags'])

        task.updated_at = utcnow()
        db.session.commit()
        return self.tasks.get_with_relations(task.id)

    def delete(self, task_id):
        task = self.get_required(task_id)
        self.tasks.delete(task)
        db.session.commit()

    def stats(self):
        counts = self.tasks.status_counts()
        total = sum(counts.values())
        done = counts.get('done', 0)
        now = utcnow()
        overdue = sum(1 for task in self.tasks.all_with_due_date() if task.is_overdue(now))
        return {
            'total': total,
            'pending': counts.get('pending', 0),
            'in_progress': counts.get('in_progress', 0),
            'done': done,
            'cancelled': counts.get('cancelled', 0),
            'overdue': overdue,
            'completion_rate': calculate_percentage(done, total),
        }
