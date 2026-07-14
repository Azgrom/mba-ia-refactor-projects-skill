"""Test harness: disposable in-memory database, import-safe app factory (F-007)."""
import os
from datetime import timedelta

import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret-key-not-for-production')

from app import create_app, init_db  # noqa: E402
from database import db  # noqa: E402
from models.category import Category  # noqa: E402
from models.task import Task  # noqa: E402
from models.user import User  # noqa: E402
from timeutil import utcnow  # noqa: E402

ADMIN_EMAIL = 'joao@email.com'
USER_EMAIL = 'maria@email.com'
MANAGER_EMAIL = 'pedro@email.com'
ADMIN_PASSWORD = 'joao-dev-1234'
USER_PASSWORD = 'maria-dev-1234'
MANAGER_PASSWORD = 'pedro-dev-1234'


@pytest.fixture
def app():
    app = create_app({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key-not-for-production',
        'TOKEN_TTL_SECONDS': 3600,
        'DEBUG': False,
    })
    init_db(app)
    with app.app_context():
        app.config['_SEED_IDS'] = _seed()
        yield app
        db.session.remove()


def _seed():
    now = utcnow()
    admin = User(); admin.name = 'João Silva'; admin.email = ADMIN_EMAIL; admin.set_password(ADMIN_PASSWORD); admin.role = 'admin'
    user = User(); user.name = 'Maria Santos'; user.email = USER_EMAIL; user.set_password(USER_PASSWORD); user.role = 'user'
    manager = User(); manager.name = 'Pedro Oliveira'; manager.email = MANAGER_EMAIL; manager.set_password(MANAGER_PASSWORD); manager.role = 'manager'
    db.session.add_all([admin, user, manager]); db.session.commit()

    cats = []
    for name, color in [('Backend', '#3498db'), ('Frontend', '#2ecc71'), ('DevOps', '#e74c3c'), ('Bug', '#e67e22')]:
        c = Category(); c.name = name; c.description = name; c.color = color
        db.session.add(c); cats.append(c)
    db.session.commit()

    specs = [
        ('Implementar autenticação JWT', 'pending', 1, admin, cats[0], now - timedelta(days=3)),
        ('Criar tela de login', 'in_progress', 2, user, cats[1], now + timedelta(days=5)),
        ('Configurar CI/CD', 'done', 2, manager, cats[2], None),
        ('Corrigir bug no filtro', 'pending', 1, admin, cats[3], now - timedelta(days=1)),
        ('Adicionar paginação', 'pending', 3, admin, cats[0], now + timedelta(days=10)),
        ('Escrever testes', 'pending', 2, user, cats[0], None),
        ('Documentar API', 'cancelled', 4, manager, cats[0], None),
        ('Refatorar models', 'in_progress', 3, user, cats[0], None),
        ('Configurar monitoramento', 'pending', 4, manager, cats[2], now + timedelta(days=20)),
        ('Melhorar validações', 'pending', 3, admin, cats[0], None),
    ]
    for title, status, priority, owner, cat, due in specs:
        t = Task(); t.title = title; t.description = title; t.status = status
        t.priority = priority; t.user_id = owner.id; t.category_id = cat.id; t.due_date = due
        db.session.add(t)
    db.session.commit()

    return {'admin_id': admin.id, 'member_id': user.id, 'manager_id': manager.id}


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded(app):
    return app.config['_SEED_IDS']


def _token(client, email, password):
    resp = client.post('/login', json={'email': email, 'password': password})
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()['token']


@pytest.fixture
def admin_auth(client):
    return {'Authorization': f'Bearer {_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)}'}


@pytest.fixture
def user_auth(client):
    return {'Authorization': f'Bearer {_token(client, USER_EMAIL, USER_PASSWORD)}'}
