"""Script para popular o banco com dados iniciais."""
from datetime import timedelta

from sqlalchemy import delete, func, select

from app import app, init_db
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from timeutil import utcnow

# Passwords are now hashed with a salted adaptive hash (F-004). The old 4-character
# fixtures are gone: the minimum is 8 characters and these are development-only.
USERS = [
    {'name': 'João Silva', 'email': 'joao@email.com', 'password': 'joao-dev-1234', 'role': 'admin'},
    {'name': 'Maria Santos', 'email': 'maria@email.com', 'password': 'maria-dev-1234', 'role': 'user'},
    {'name': 'Pedro Oliveira', 'email': 'pedro@email.com', 'password': 'pedro-dev-1234', 'role': 'manager'},
]

CATEGORIES = [
    {'name': 'Backend', 'description': 'Tarefas de backend', 'color': '#3498db'},
    {'name': 'Frontend', 'description': 'Tarefas de frontend', 'color': '#2ecc71'},
    {'name': 'DevOps', 'description': 'Tarefas de infraestrutura', 'color': '#e74c3c'},
    {'name': 'Bug', 'description': 'Correção de bugs', 'color': '#e67e22'},
]


def seed_data():
    init_db(app)

    with app.app_context():
        now = utcnow()

        db.session.execute(delete(Task))
        db.session.execute(delete(User))
        db.session.execute(delete(Category))
        db.session.commit()

        users = []
        for spec in USERS:
            user = User()
            user.name = spec['name']
            user.email = spec['email']
            user.set_password(spec['password'])
            user.role = spec['role']
            db.session.add(user)
            users.append(user)

        categories = []
        for spec in CATEGORIES:
            category = Category()
            category.name = spec['name']
            category.description = spec['description']
            category.color = spec['color']
            db.session.add(category)
            categories.append(category)

        db.session.commit()

        u1, u2, u3 = users
        c1, c2, c3, c4 = categories

        tasks_data = [
            {'title': 'Implementar autenticação JWT', 'description': 'Adicionar autenticação real com JWT', 'status': 'pending', 'priority': 1, 'user_id': u1.id, 'category_id': c1.id, 'due_date': now - timedelta(days=3)},
            {'title': 'Criar tela de login', 'description': 'Tela de login responsiva', 'status': 'in_progress', 'priority': 2, 'user_id': u2.id, 'category_id': c2.id, 'due_date': now + timedelta(days=5)},
            {'title': 'Configurar CI/CD', 'description': 'Pipeline com GitHub Actions', 'status': 'done', 'priority': 2, 'user_id': u3.id, 'category_id': c3.id, 'tags': 'devops,ci,github'},
            {'title': 'Corrigir bug no filtro de busca', 'description': 'Filtro não funciona com caracteres especiais', 'status': 'pending', 'priority': 1, 'user_id': u1.id, 'category_id': c4.id, 'due_date': now - timedelta(days=1)},
            {'title': 'Adicionar paginação na API', 'description': 'Endpoints retornam todos os registros', 'status': 'pending', 'priority': 3, 'user_id': u1.id, 'category_id': c1.id, 'due_date': now + timedelta(days=10)},
            {'title': 'Escrever testes unitários', 'description': 'Cobertura mínima de 80%', 'status': 'pending', 'priority': 2, 'user_id': u2.id, 'category_id': c1.id},
            {'title': 'Documentar API com Swagger', 'description': 'Gerar documentação automática', 'status': 'cancelled', 'priority': 4, 'user_id': u3.id, 'category_id': c1.id},
            {'title': 'Refatorar models', 'description': 'Melhorar organização dos models', 'status': 'in_progress', 'priority': 3, 'user_id': u2.id, 'category_id': c1.id, 'tags': 'refactor,tech-debt'},
            {'title': 'Configurar monitoramento', 'description': 'Prometheus + Grafana', 'status': 'pending', 'priority': 4, 'user_id': u3.id, 'category_id': c3.id, 'due_date': now + timedelta(days=20)},
            {'title': 'Melhorar validações de input', 'description': 'Usar marshmallow ou pydantic', 'status': 'pending', 'priority': 3, 'user_id': u1.id, 'category_id': c1.id, 'tags': 'improvement,validation'},
        ]

        for spec in tasks_data:
            task = Task()
            task.title = spec['title']
            task.description = spec['description']
            task.status = spec['status']
            task.priority = spec['priority']
            task.user_id = spec['user_id']
            task.category_id = spec['category_id']
            task.due_date = spec.get('due_date')
            task.tags = spec.get('tags')
            db.session.add(task)

        db.session.commit()

        def count(model):
            return db.session.execute(select(func.count()).select_from(model)).scalar_one()

        print('Seed concluído com sucesso!')
        print(f'  {count(User)} usuários')
        print(f'  {count(Category)} categorias')
        print(f'  {count(Task)} tasks')
        print('  Login de desenvolvimento: joao@email.com / joao-dev-1234')


if __name__ == '__main__':
    seed_data()
