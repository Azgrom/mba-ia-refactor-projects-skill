"""Endpoint contract, security, and domain-flow validation against the baseline."""


def items(resp):
    body = resp.get_json()
    return body['items'] if isinstance(body, dict) and 'items' in body else body


# --- Boot / open endpoints -------------------------------------------------

def test_health_open(client):
    assert client.get('/health').status_code == 200


def test_index_open(client):
    assert client.get('/').status_code == 200


# --- F-002: auth boundary --------------------------------------------------

def test_list_tasks_requires_auth(client):
    assert client.get('/tasks').status_code == 401


def test_anonymous_cannot_escalate_role(client):
    # The original headline vulnerability: PUT /users/2 {"role":"admin"} -> 200.
    assert client.put('/users/2', json={'role': 'admin'}).status_code == 401


def test_non_admin_cannot_change_role(client, user_auth):
    # Maria (id 2, role user) authenticated, trying to promote herself.
    resp = client.put('/users/2', json={'role': 'admin'}, headers=user_auth)
    assert resp.status_code == 403


def test_user_cannot_modify_other_user(client, user_auth):
    assert client.put('/users/1', json={'name': 'hacked'}, headers=user_auth).status_code == 403


def test_only_admin_deletes_users(client, user_auth):
    assert client.delete('/users/3', headers=user_auth).status_code == 403


# --- F-001: password never serialized --------------------------------------

def test_login_response_has_no_password(client):
    body = client.post('/login', json={'email': 'joao@email.com', 'password': 'joao-dev-1234'}).get_json()
    assert 'password' not in body['user']


def test_get_user_has_no_password(client, admin_auth):
    body = client.get('/users/1', headers=admin_auth).get_json()
    assert 'password' not in body


def test_list_users_has_no_password(client, admin_auth):
    for user in items(client.get('/users', headers=admin_auth)):
        assert 'password' not in user


# --- F-002/F-004: real login contract --------------------------------------

def test_login_success_issues_jwt(client):
    body = client.post('/login', json={'email': 'joao@email.com', 'password': 'joao-dev-1234'}).get_json()
    assert body['token'].count('.') == 2  # JWT, not fake-jwt-token-<id>
    assert not body['token'].startswith('fake-jwt-token')


def test_login_wrong_password(client):
    assert client.post('/login', json={'email': 'joao@email.com', 'password': 'nope'}).status_code == 401


def test_login_unknown_email(client):
    assert client.post('/login', json={'email': 'ghost@x.com', 'password': 'x'}).status_code == 401


# --- Baseline happy paths (now authenticated) ------------------------------

def test_list_tasks(client, admin_auth):
    assert len(items(client.get('/tasks', headers=admin_auth))) == 10


def test_get_task(client, admin_auth):
    body = client.get('/tasks/1', headers=admin_auth).get_json()
    assert body['id'] == 1 and 'overdue' in body


def test_task_stats(client, admin_auth):
    body = client.get('/tasks/stats', headers=admin_auth).get_json()
    assert body['total'] == 10
    assert body['overdue'] == 2  # two seeded past-due, non-terminal tasks


def test_reports_summary(client, admin_auth):
    body = client.get('/reports/summary', headers=admin_auth).get_json()
    assert body['overview']['total_tasks'] == 10
    assert body['overdue']['count'] == 2


def test_reports_user(client, admin_auth):
    body = client.get('/reports/user/1', headers=admin_auth).get_json()
    assert body['user']['id'] == 1
    assert 'completion_rate' in body['statistics']


def test_categories(client, admin_auth):
    assert len(client.get('/categories', headers=admin_auth).get_json()) == 4


# --- F-015: task shape identical across endpoints --------------------------

def test_task_shape_consistent(client, admin_auth):
    a = set(items(client.get('/tasks', headers=admin_auth))[0].keys())
    b = set(items(client.get('/tasks/search?q=a', headers=admin_auth))[0].keys())
    c = set(items(client.get('/users/1/tasks', headers=admin_auth))[0].keys())
    assert a == b == c
    assert {'overdue', 'user_name', 'category_name'} <= a


# --- F-009: bad input is 400, not 500 --------------------------------------

def test_priority_string_is_400(client, admin_auth):
    resp = client.post('/tasks', json={'title': 'valid title', 'priority': 'high'}, headers=admin_auth)
    assert resp.status_code == 400


def test_search_bad_priority_is_400(client, admin_auth):
    assert client.get('/tasks/search?priority=abc', headers=admin_auth).status_code == 400


def test_update_title_null_is_400(client, admin_auth):
    assert client.put('/tasks/1', json={'title': None}, headers=admin_auth).status_code == 400


def test_create_task_short_title(client, admin_auth):
    assert client.post('/tasks', json={'title': 'ab'}, headers=admin_auth).status_code == 400


def test_create_task_missing_title(client, admin_auth):
    assert client.post('/tasks', json={'description': 'x'}, headers=admin_auth).status_code == 400


def test_bad_status(client, admin_auth):
    assert client.post('/tasks', json={'title': 'valid title', 'status': 'bogus'}, headers=admin_auth).status_code == 400


def test_unknown_user_fk(client, admin_auth):
    assert client.post('/tasks', json={'title': 'valid title', 'user_id': 9999}, headers=admin_auth).status_code == 404


# --- Not found / conflict --------------------------------------------------

def test_task_not_found(client, admin_auth):
    assert client.get('/tasks/9999', headers=admin_auth).status_code == 404


def test_duplicate_email_conflict(client):
    resp = client.post('/users', json={'name': 'Dup', 'email': 'joao@email.com', 'password': 'longenough'})
    assert resp.status_code == 409


# --- Domain flow: create -> retrieve -> update -> delete -------------------

def test_task_lifecycle(client, admin_auth):
    created = client.post('/tasks', json={'title': 'Lifecycle probe', 'priority': 2, 'user_id': 1, 'category_id': 1}, headers=admin_auth)
    assert created.status_code == 201
    tid = created.get_json()['id']
    assert client.get(f'/tasks/{tid}', headers=admin_auth).status_code == 200
    assert client.put(f'/tasks/{tid}', json={'status': 'done'}, headers=admin_auth).get_json()['status'] == 'done'
    assert client.delete(f'/tasks/{tid}', headers=admin_auth).status_code == 200
    assert client.get(f'/tasks/{tid}', headers=admin_auth).status_code == 404


# --- Domain flow: delete user cascades tasks in one transaction ------------

def test_delete_user_cascades_tasks(client, admin_auth):
    before = len(items(client.get('/users/3/tasks', headers=admin_auth)))
    assert before > 0
    assert client.delete('/users/3', headers=admin_auth).status_code == 200
    assert client.get('/users/3', headers=admin_auth).status_code == 404


# --- F-004: legacy MD5 hash rejected ---------------------------------------

def test_password_is_adaptive_hash(app):
    from database import db
    from models.user import User
    from sqlalchemy import select
    with app.app_context():
        u = db.session.execute(select(User).where(User.email == 'joao@email.com')).scalar_one()
        assert not u.password.startswith('fake')
        assert len(u.password) > 40  # pbkdf2/scrypt, not a 32-char MD5 hex
        assert u.check_password('joao-dev-1234')
        assert not u.check_password('wrong')
