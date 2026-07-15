"""Authentication boundary (F-002).

Before this existed, `/login` returned `fake-jwt-token-<id>` and nothing in the
application ever read an Authorization header — every endpoint, including
`DELETE /users/<id>` and role changes, was reachable anonymously.
"""
from datetime import timedelta
from functools import wraps

import jwt
from flask import current_app, g, request

from errors import AuthenticationError, AuthorizationError
from timeutil import utcnow

ALGORITHM = 'HS256'


def issue_token(user):
    now = utcnow()
    ttl = int(current_app.config['TOKEN_TTL_SECONDS'])
    payload = {
        'sub': str(user.id),
        'role': user.role,
        'iat': now,
        'exp': now + timedelta(seconds=ttl),
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm=ALGORITHM)


def decode_token(token):
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError('Token expirado') from None
    except jwt.InvalidTokenError:
        raise AuthenticationError('Token inválido') from None


def _bearer_token():
    header = request.headers.get('Authorization', '')
    scheme, _, token = header.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise AuthenticationError('Autenticação obrigatória')
    return token.strip()


def current_user():
    user = getattr(g, 'current_user', None)
    if user is None:
        raise AuthenticationError('Autenticação obrigatória')
    return user


def authenticate():
    """Resolve the caller from the bearer token and pin it to the request."""
    from repositories.user_repository import UserRepository

    payload = decode_token(_bearer_token())
    try:
        user_id = int(payload.get('sub'))
    except (TypeError, ValueError):
        raise AuthenticationError('Token inválido') from None

    user = UserRepository().get(user_id)
    if not user:
        raise AuthenticationError('Token inválido')
    if not user.active:
        raise AuthorizationError('Usuário inativo')

    g.current_user = user
    return user


def optional_authenticate():
    """Resolve the caller if a token is present; return None when anonymous.

    Used by public registration, where an admin may set a role but an anonymous
    caller may not.
    """
    if not request.headers.get('Authorization'):
        return None
    return authenticate()


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        authenticate()
        return view(*args, **kwargs)

    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = authenticate()
        if not user.is_admin():
            raise AuthorizationError('Acesso negado: requer perfil admin')
        return view(*args, **kwargs)

    return wrapper


def require_self_or_admin(user_id):
    """Ownership check: a user may act on themselves; an admin on anyone."""
    user = current_user()
    if user.id != user_id and not user.is_admin():
        raise AuthorizationError('Acesso negado')
    return user
