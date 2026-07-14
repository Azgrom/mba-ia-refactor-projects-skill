"""Report transport. Category CRUD moved to routes/category_routes.py (F-016)."""
from flask import Blueprint, jsonify

from security import require_auth
from services.report_service import ReportService

report_bp = Blueprint('reports', __name__)
reports = ReportService()


@report_bp.route('/reports/summary', methods=['GET'])
@require_auth
def summary_report():
    return jsonify(reports.summary()), 200


@report_bp.route('/reports/user/<int:user_id>', methods=['GET'])
@require_auth
def user_report(user_id):
    return jsonify(reports.for_user(user_id)), 200
