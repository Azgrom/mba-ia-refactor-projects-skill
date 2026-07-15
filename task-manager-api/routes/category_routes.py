"""Category transport (F-016).

These four endpoints previously lived on the reports blueprint. The paths and
methods are unchanged; only the owning module moved.
"""
from flask import Blueprint, jsonify, request

from security import require_admin, require_auth
from serializers import serialize_category
from services.category_service import CategoryService
from validators import require_json

category_bp = Blueprint('categories', __name__)
categories = CategoryService()


@category_bp.route('/categories', methods=['GET'])
@require_auth
def get_categories():
    return jsonify([
        serialize_category(category, task_count)
        for category, task_count in categories.list_with_counts()
    ]), 200


@category_bp.route('/categories', methods=['POST'])
@require_auth
def create_category():
    category = categories.create(require_json(request.get_json(silent=True)))
    return jsonify(serialize_category(category)), 201


@category_bp.route('/categories/<int:cat_id>', methods=['PUT'])
@require_auth
def update_category(cat_id):
    category = categories.update(cat_id, require_json(request.get_json(silent=True)))
    return jsonify(serialize_category(category)), 200


@category_bp.route('/categories/<int:cat_id>', methods=['DELETE'])
@require_admin
def delete_category(cat_id):
    categories.delete(cat_id)
    return jsonify({'message': 'Categoria deletada'}), 200
