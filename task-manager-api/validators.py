"""Boundary validation and coercion (F-009).

Every message here is byte-identical to the one the corresponding route returned
before the refactor, so the 400 contract is preserved. The difference is that
inputs which previously raised TypeError/ValueError (and surfaced as 500) now
raise ValidationError and surface as 400.
"""
from datetime import datetime, timezone

from errors import ValidationError

VALID_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
VALID_ROLES = ('user', 'admin', 'manager')
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PRIORITY = 1
MAX_PRIORITY = 5
MIN_PASSWORD_LENGTH = 8
DEFAULT_PRIORITY = 3
DEFAULT_COLOR = '#000000'
DATE_FORMAT = '%Y-%m-%d'

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

EMAIL_PATTERN = r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'


def require_json(data):
    if not data or not isinstance(data, dict):
        raise ValidationError('Dados inválidos')
    return data


def parse_title(value, message_short='Título muito curto', message_long='Título muito longo'):
    if not isinstance(value, str):
        raise ValidationError(message_short)
    if len(value) < MIN_TITLE_LENGTH:
        raise ValidationError(message_short)
    if len(value) > MAX_TITLE_LENGTH:
        raise ValidationError(message_long)
    return value


def parse_status(value):
    if value not in VALID_STATUSES:
        raise ValidationError('Status inválido')
    return value


def parse_priority(value):
    # The old code compared `value < 1` directly, so a JSON string raised
    # TypeError and returned 500. Coerce first, reject non-numerics as 400.
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValidationError('Prioridade deve ser entre 1 e 5')
    try:
        priority = int(value)
    except (TypeError, ValueError):
        raise ValidationError('Prioridade deve ser entre 1 e 5') from None
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')
    return priority


def parse_role(value):
    if value not in VALID_ROLES:
        raise ValidationError('Role inválido')
    return value


def parse_due_date(value, message='Formato de data inválido. Use YYYY-MM-DD'):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        parsed = datetime.strptime(value, DATE_FORMAT)
    except ValueError:
        raise ValidationError(message) from None
    return parsed.replace(tzinfo=timezone.utc)


def parse_tags(value):
    if value is None:
        return None
    if isinstance(value, list):
        if not all(isinstance(tag, str) for tag in value):
            raise ValidationError('Tags inválidas')
        return ','.join(value)
    if isinstance(value, str):
        return value
    raise ValidationError('Tags inválidas')


def parse_email(value):
    import re

    if not isinstance(value, str) or not re.match(EMAIL_PATTERN, value):
        raise ValidationError('Email inválido')
    return value


def parse_password(value, message='Senha muito curta'):
    if not isinstance(value, str) or len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(message)
    return value


def parse_name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError('Nome é obrigatório')
    return value.strip()


def parse_optional_int(value, message):
    """Coerce an optional query-string integer; reject garbage as 400 not 500."""
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(message) from None


def parse_pagination(args):
    """Bounded pagination for list endpoints (F-010)."""
    page = parse_optional_int(args.get('page'), 'Página inválida') or 1
    per_page = parse_optional_int(args.get('per_page'), 'per_page inválido') or DEFAULT_PAGE_SIZE
    if page < 1:
        raise ValidationError('Página inválida')
    if per_page < 1 or per_page > MAX_PAGE_SIZE:
        raise ValidationError(f'per_page deve ser entre 1 e {MAX_PAGE_SIZE}')
    return page, per_page
