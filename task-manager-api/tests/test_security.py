"""Security regressions for F-001, F-002, F-003, F-004, F-006.

Each test encodes an attack that SUCCEEDED against the original code.
"""
import json

import pytest

from config import ConfigError, load_config
from conftest import ADMIN_PASSWORD, USER_PASSWORD

PROTECTED = [
    ('get', '/tasks'),
    ('get', '/tasks/1'),
    ('post', '/tasks'),
    ('put', '/tasks/1'),
    ('delete', '/tasks/1'),
    ('get', '/tasks/search'),
    ('get', '/tasks/stats'),
    ('get', '/users'),
    ('get', '/users/1'),
    ('put', '/users/1'),
    ('delete', '/users/1'),
    ('get', '/users/1/tasks'),
    ('get', '/categories'),
    ('post', '/categories'),
    ('put', '/categories/1'),
    ('delete', '/categories/1'),
    ('get', '/reports/summary'),
    ('get', '/reports/user/1'),
]


@pytest.mark.parametrize('method,path', PROTECTED)
def test_every_protected_endpoint_rejects_anonymous_access(client, seeded, method, path):
    """F-002: all 18 of these returned 200 to an anonymous caller before."""
    response = getattr(client, method)(path, json={})
    assert response.status_code == 401, f'{method.upper()} {path} allowed anonymous access'


def test_public_endpoints_remain_public(client, seeded):
    assert client.get('/').status_code == 200
    assert client.get('/health').status_code == 200
    assert client.post('/login', json={'email': 'x@y.z', 'password': 'nope'}).status_code == 401


def test_password_hash_never_appears_in_any_response(client, seeded, admin_auth):
    """F-001: GET /users/<id>, POST /users and POST /login all leaked the hash."""
    login = client.post('/login', json={'email': 'joao@email.com', 'password': ADMIN_PASSWORD})
    created = client.post('/users', json={
        'name': 'Probe', 'email': 'probe@email.com', 'password': 'probe-pass-1234',
    })
    responses = [
        login,
        created,
        client.get(f'/users/{seeded["admin_id"]}', headers=admin_auth),
        client.get('/users', headers=admin_auth),
    ]
    for response in responses:
        body = json.dumps(response.get_json())
        assert 'password' not in body, f'password field leaked: {response.request.path}'
        assert 'pbkdf2' not in body and 'scrypt' not in body, 'hash value leaked'


def test_anonymous_cannot_escalate_role(client, seeded):
    """F-002: PUT /users/<id> {"role":"admin"} returned 200 with no credentials."""
    response = client.put(f'/users/{seeded["member_id"]}', json={'role': 'admin'})
    assert response.status_code == 401


def test_non_admin_cannot_escalate_own_role(client, seeded, user_auth):
    """Authenticated but non-admin self-promotion must be refused."""
    response = client.put(f'/users/{seeded["member_id"]}', json={'role': 'admin'},
                          headers=user_auth)
    assert response.status_code == 403


def test_non_admin_cannot_modify_another_user(client, seeded, user_auth):
    response = client.put(f'/users/{seeded["admin_id"]}', json={'name': 'Hacked'},
                          headers=user_auth)
    assert response.status_code == 403


def test_non_admin_cannot_delete_user(client, seeded, user_auth):
    response = client.delete(f'/users/{seeded["admin_id"]}', headers=user_auth)
    assert response.status_code == 403


def test_admin_can_delete_user(client, seeded, admin_auth):
    response = client.delete(f'/users/{seeded["manager_id"]}', headers=admin_auth)
    assert response.status_code == 200


def test_anonymous_registration_cannot_self_assign_admin_role(client, seeded):
    """Registration is public, so role must not be caller-controlled."""
    response = client.post('/users', json={
        'name': 'Sneaky', 'email': 'sneaky@email.com',
        'password': 'sneaky-pass-1234', 'role': 'admin',
    })
    assert response.status_code == 403


def test_token_is_not_forgeable_by_string_construction(client, seeded):
    """F-002: the old token was literally 'fake-jwt-token-' + user id."""
    forged = {'Authorization': f'Bearer fake-jwt-token-{seeded["admin_id"]}'}
    assert client.get('/users', headers=forged).status_code == 401


def test_boot_requires_secret_key(monkeypatch):
    """F-003: SECRET_KEY has no default; a missing one must fail fast at load."""
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(ConfigError):
        load_config({'SECRET_KEY': ''})


def test_config_defaults_debug_off_and_loopback():
    """F-006: debug is off and host is loopback unless explicitly configured."""
    config = load_config({'SECRET_KEY': 'present'})
    assert config['DEBUG'] is False
    assert config['HOST'] == '127.0.0.1'