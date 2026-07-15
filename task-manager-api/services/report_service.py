"""Reporting use cases (F-005, F-008).

The summary report previously issued 19 queries: eleven separate count() calls,
a full table load, and one more task query per user. It is now a fixed set of
grouped aggregates that does not grow with the number of users.
"""
from datetime import timedelta

from errors import NotFoundError
from repositories.category_repository import CategoryRepository
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from utils.helpers import calculate_percentage
from timeutil import ensure_utc, isoformat, utcnow

PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}


class ReportService:
    def __init__(self, tasks=None, users=None, categories=None):
        self.tasks = tasks or TaskRepository()
        self.users = users or UserRepository()
        self.categories = categories or CategoryRepository()

    def summary(self):
        now = utcnow()
        seven_days_ago = now - timedelta(days=7)

        status_counts = self.tasks.status_counts()
        priority_counts = self.tasks.priority_counts()

        overdue_tasks = [task for task in self.tasks.all_with_due_date() if task.is_overdue(now)]
        overdue_list = [
            {
                'id': task.id,
                'title': task.title,
                'due_date': isoformat(task.due_date),
                'days_overdue': (now - ensure_utc(task.due_date)).days,
            }
            for task in overdue_tasks
        ]

        # One grouped (user_id, status) aggregate instead of a query per user.
        per_user = {}
        for user_id, status, count in self.tasks.list_for_user_ids():
            bucket = per_user.setdefault(user_id, {'total': 0, 'done': 0})
            bucket['total'] += count
            if status == 'done':
                bucket['done'] += count

        user_stats = []
        for user in self.users.all():
            bucket = per_user.get(user.id, {'total': 0, 'done': 0})
            user_stats.append(
                {
                    'user_id': user.id,
                    'user_name': user.name,
                    'total_tasks': bucket['total'],
                    'completed_tasks': bucket['done'],
                    'completion_rate': calculate_percentage(bucket['done'], bucket['total']),
                }
            )

        return {
            'generated_at': isoformat(now),
            'overview': {
                'total_tasks': sum(status_counts.values()),
                'total_users': self.users.total(),
                'total_categories': self.categories.total(),
            },
            'tasks_by_status': {
                'pending': status_counts.get('pending', 0),
                'in_progress': status_counts.get('in_progress', 0),
                'done': status_counts.get('done', 0),
                'cancelled': status_counts.get('cancelled', 0),
            },
            'tasks_by_priority': {
                label: priority_counts.get(priority, 0)
                for priority, label in PRIORITY_LABELS.items()
            },
            'overdue': {
                'count': len(overdue_list),
                'tasks': overdue_list,
            },
            'recent_activity': {
                'tasks_created_last_7_days': self.tasks.created_since(seven_days_ago),
                'tasks_completed_last_7_days': self.tasks.completed_since(seven_days_ago),
            },
            'user_productivity': user_stats,
        }

    def for_user(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')

        now = utcnow()
        tasks = self.tasks.list_for_user_all(user_id)

        counts = {'done': 0, 'pending': 0, 'in_progress': 0, 'cancelled': 0}
        overdue = 0
        high_priority = 0
        for task in tasks:
            if task.status in counts:
                counts[task.status] += 1
            if task.priority is not None and task.priority <= 2:
                high_priority += 1
            if task.is_overdue(now):
                overdue += 1

        total = len(tasks)
        return {
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
            },
            'statistics': {
                'total_tasks': total,
                'done': counts['done'],
                'pending': counts['pending'],
                'in_progress': counts['in_progress'],
                'cancelled': counts['cancelled'],
                'overdue': overdue,
                'high_priority': high_priority,
                'completion_rate': calculate_percentage(counts['done'], total),
            },
        }
