"""User use cases (F-005). Owns orchestration and the transaction boundary."""
from database import db
from errors import AuthenticationError, AuthorizationError, ConflictError, NotFoundError, ValidationError
from models.user import User
from repositories.task_repository import TaskRepository
from repositories.user_repository import UserRepository
from validators import MIN_PASSWORD_LENGTH, parse_email, parse_name, parse_password, parse_role


class UserService:
    def __init__(self, users=None, tasks=None):
        self.users = users or UserRepository()
        self.tasks = tasks or TaskRepository()

    def get_required(self, user_id):
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError('Usuário não encontrado')
        return user

    def list(self, page, per_page):
        users, total = self.users.paginate(page, per_page)
        counts = self.users.task_counts()
        return users, counts, total

    def register(self, data, actor=None):
        name = parse_name(data.get('name')) if data.get('name') else _require('Nome é obrigatório')
        if not data.get('email'):
            _require('Email é obrigatório')
        if not data.get('password'):
            _require('Senha é obrigatória')

        email = parse_email(data['email'])
        password = parse_password(
            data['password'],
            message=f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres',
        )

        if self.users.find_by_email(email):
            raise ConflictError('Email já cadastrado')

        # Registration is public, so an anonymous caller must not be able to
        # hand themselves a privileged role (F-002). Only an admin may set one.
        requested_role = data.get('role', 'user')
        if requested_role != 'user':
            if actor is None or not actor.is_admin():
                raise AuthorizationError('Apenas admins podem definir role')
            requested_role = parse_role(requested_role)

        user = User()
        user.name = name
        user.email = email
        user.set_password(password)
        user.role = requested_role

        self.users.add(user)
        db.session.commit()
        return user

    def update(self, user_id, data, actor):
        user = self.get_required(user_id)

        if 'name' in data:
            user.name = parse_name(data['name'])

        if 'email' in data:
            email = parse_email(data['email'])
            existing = self.users.find_by_email(email)
            if existing and existing.id != user_id:
                raise ConflictError('Email já cadastrado')
            user.email = email

        if 'password' in data:
            user.set_password(parse_password(data['password']))

        # Privilege fields are admin-only; previously anyone could self-promote.
        if 'role' in data:
            if not actor.is_admin():
                raise AuthorizationError('Apenas admins podem alterar role')
            user.role = parse_role(data['role'])

        if 'active' in data:
            if not actor.is_admin():
                raise AuthorizationError('Apenas admins podem alterar active')
            if not isinstance(data['active'], bool):
                raise ValidationError('active deve ser booleano')
            user.active = data['active']

        db.session.commit()
        return user

    def delete(self, user_id):
        """Deletes the user and their tasks in one transaction."""
        user = self.get_required(user_id)
        for task in self.tasks.list_for_user_all(user_id):
            self.tasks.delete(task)
        self.users.delete(user)
        db.session.commit()

    def authenticate(self, email, password):
        if not email or not password:
            raise ValidationError('Email e senha são obrigatórios')

        user = self.users.find_by_email(email)
        # Same error for unknown email and wrong password: do not leak which
        # addresses are registered.
        if not user or not user.check_password(password):
            raise AuthenticationError('Credenciais inválidas')
        if not user.active:
            raise AuthorizationError('Usuário inativo')
        return user


def _require(message):
    raise ValidationError(message)
