"""Environment-driven configuration (F-003, F-007)."""
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULTS = {
    'SQLALCHEMY_DATABASE_URI': 'sqlite:///tasks.db',
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'DEBUG': False,
    'HOST': '127.0.0.1',
    'PORT': 5000,
    'TOKEN_TTL_SECONDS': 3600,
    'CORS_ORIGINS': '',
}

_TRUTHY = {'1', 'true', 'yes', 'on'}


class ConfigError(RuntimeError):
    """Raised at boot when required configuration is missing."""


def _flag(raw, fallback):
    if raw is None:
        return fallback
    return raw.strip().lower() in _TRUTHY


def _int(raw, fallback):
    if raw is None or not str(raw).strip():
        return fallback
    try:
        return int(raw)
    except ValueError as error:
        raise ConfigError(f'Expected an integer, got {raw!r}') from error


def load_config(overrides=None):
    """Build the Flask config mapping from defaults, environment, then overrides.

    SECRET_KEY has no default on purpose: booting without it must fail loudly
    rather than silently signing tokens with a well-known value.
    """
    config = dict(DEFAULTS)

    env = os.environ
    if 'SECRET_KEY' in env:
        config['SECRET_KEY'] = env['SECRET_KEY']
    if 'DATABASE_URI' in env:
        config['SQLALCHEMY_DATABASE_URI'] = env['DATABASE_URI']
    config['DEBUG'] = _flag(env.get('DEBUG'), config['DEBUG'])
    config['HOST'] = env.get('HOST', config['HOST'])
    config['PORT'] = _int(env.get('PORT'), config['PORT'])
    config['TOKEN_TTL_SECONDS'] = _int(env.get('TOKEN_TTL_SECONDS'), config['TOKEN_TTL_SECONDS'])
    config['CORS_ORIGINS'] = env.get('CORS_ORIGINS', config['CORS_ORIGINS'])

    if overrides:
        config.update(overrides)

    if not config.get('SECRET_KEY'):
        raise ConfigError(
            'SECRET_KEY is required and has no default. '
            'Copy .env.example to .env and set SECRET_KEY, or pass it to create_app().'
        )

    return config


def cors_origins(config):
    """Parse CORS_ORIGINS into a list; empty means same-origin only (F-002)."""
    raw = (config.get('CORS_ORIGINS') or '').strip()
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(',') if origin.strip()]
