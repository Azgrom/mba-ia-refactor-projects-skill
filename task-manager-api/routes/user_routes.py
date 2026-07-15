"""User and authentication transport."""
from flask import Blueprint, g, jsonify, request

from security import (
    issue_token,
    optional_authenticate,
    require_admin,
    require_auth,
    require_self_or_admin,
)
from serializers import (
    paginated,
    serialize_task_with_relations,
    serialize_user,
    serialize_user_with_task_count,
)
from services.task_service import TaskService
from services.user_service import UserService
from timeutil import utcnow
from validators import parse_pagination, require_json

user_bp = Blueprint('users', __name__)
users = UserService()
tasks = TaskService()


@user_bp.route('/users', methods=['GET'])
@require_auth
def get_users():
    page, per_page = parse_pagination(request.args)
    rows, counts, total = users.list(page, per_page)
    items = [serialize_user_with_task_count(user, counts.get(user.id, 0)) for user in rows]
    return jsonify(paginated(items, page, per_page, total)), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    user = users.get_required(user_id)
    page, per_page = parse_pagination(request.args)
    rows, total = tasks.list(page, per_page, user_id=user_id)
    now = utcnow()

    data = serialize_user(user)
    data['tasks'] = [serialize_task_with_relations(task, now) for task in rows]
    data['tasks_pagination'] = paginated([], page, per_page, total)['pagination']
    return jsonify(data), 200


@user_bp.route('/users', methods=['POST'])
def create_user():
    # Public registration. An authenticated admin may additionally assign a role;
    # an anonymous caller may not (see UserService.register).
    actor = optional_authenticate()
    user = users.register(require_json(request.get_json(silent=True)), actor=actor)
    return jsonify(serialize_user(user)), 201


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id):
    actor = require_self_or_admin(user_id)
    user = users.update(user_id, require_json(request.get_json(silent=True)), actor=actor)
    return jsonify(serialize_user(user)), 200


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    users.delete(user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
@require_auth
def get_user_tasks(user_id):
    users.get_required(user_id)
    page, per_page = parse_pagination(request.args)
    rows, total = tasks.list(page, per_page, user_id=user_id)
    now = utcnow()
    items = [serialize_task_with_relations(task, now) for task in rows]
    return jsonify(paginated(items, page, per_page, total)), 200


@user_bp.route('/login', methods=['POST'])
def login():
    data = require_json(request.get_json(silent=True))
    user = users.authenticate(data.get('email'), data.get('password'))
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': serialize_user(user),
        'token': issue_token(user),
    }), 200
