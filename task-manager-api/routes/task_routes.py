"""Task transport: parse request -> call use case -> serialize. Nothing else."""
from flask import Blueprint, jsonify, request

from security import require_auth
from serializers import paginated, serialize_task_with_relations
from services.task_service import TaskService
from timeutil import utcnow
from validators import parse_optional_int, parse_pagination, require_json

task_bp = Blueprint('tasks', __name__)
tasks = TaskService()


@task_bp.route('/tasks', methods=['GET'])
@require_auth
def get_tasks():
    page, per_page = parse_pagination(request.args)
    rows, total = tasks.list(page, per_page)
    now = utcnow()
    items = [serialize_task_with_relations(task, now) for task in rows]
    return jsonify(paginated(items, page, per_page, total)), 200


@task_bp.route('/tasks/search', methods=['GET'])
@require_auth
def search_tasks():
    page, per_page = parse_pagination(request.args)
    rows, total = tasks.list(
        page,
        per_page,
        query=request.args.get('q', ''),
        status=request.args.get('status', ''),
        priority=parse_optional_int(request.args.get('priority'), 'Prioridade inválida'),
        user_id=parse_optional_int(request.args.get('user_id'), 'user_id inválido'),
    )
    now = utcnow()
    items = [serialize_task_with_relations(task, now) for task in rows]
    return jsonify(paginated(items, page, per_page, total)), 200


@task_bp.route('/tasks/stats', methods=['GET'])
@require_auth
def task_stats():
    return jsonify(tasks.stats()), 200


@task_bp.route('/tasks/<int:task_id>', methods=['GET'])
@require_auth
def get_task(task_id):
    return jsonify(serialize_task_with_relations(tasks.get_required(task_id))), 200


@task_bp.route('/tasks', methods=['POST'])
@require_auth
def create_task():
    task = tasks.create(require_json(request.get_json(silent=True)))
    return jsonify(serialize_task_with_relations(task)), 201


@task_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@require_auth
def update_task(task_id):
    task = tasks.update(task_id, require_json(request.get_json(silent=True)))
    return jsonify(serialize_task_with_relations(task)), 200


@task_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_auth
def delete_task(task_id):
    tasks.delete(task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200
