"""Explicit response projections (F-001, F-015).

One owner per entity shape. `password` is structurally absent — it is not
filtered out, it is never put in. Task shape is now identical across /tasks,
/tasks/search and /users/<id>/tasks, which previously returned 14, 11 and 8
keys respectively for the same entity.
"""
from timeutil import isoformat


def serialize_user(user):
    """Public user projection. Never includes the password hash."""
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'active': user.active,
        'created_at': isoformat(user.created_at),
    }


def serialize_user_with_task_count(user, task_count):
    data = serialize_user(user)
    data['task_count'] = task_count
    return data


def serialize_task(task, now=None, user_name=None, category_name=None):
    """Canonical task projection used by every task-returning endpoint."""
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'user_id': task.user_id,
        'category_id': task.category_id,
        'created_at': isoformat(task.created_at),
        'updated_at': isoformat(task.updated_at),
        'due_date': isoformat(task.due_date),
        'tags': task.tag_list(),
        'overdue': task.is_overdue(now),
        'user_name': user_name,
        'category_name': category_name,
    }


def serialize_task_with_relations(task, now=None):
    """Uses the already-loaded relationships; requires eager loading to avoid N+1."""
    return serialize_task(
        task,
        now=now,
        user_name=task.user.name if task.user else None,
        category_name=task.category.name if task.category else None,
    )


def serialize_category(category, task_count=None):
    data = {
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'color': category.color,
        'created_at': isoformat(category.created_at),
    }
    if task_count is not None:
        data['task_count'] = task_count
    return data


def paginated(items, page, per_page, total):
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page if per_page else 0,
        },
    }
