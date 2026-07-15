"""Typed application errors and their single HTTP mapping (F-009).

The response body stays `{"error": "<message>"}` so existing clients that read
that shape keep working; only the status codes for previously-crashing inputs
change (500 -> 400), which is the approved contract change.
"""
import logging

logger = logging.getLogger(__name__)


class AppError(Exception):
    status = 500
    default_message = 'Erro interno'

    def __init__(self, message=None):
        self.message = message or self.default_message
        super().__init__(self.message)


class ValidationError(AppError):
    status = 400
    default_message = 'Dados inválidos'


class AuthenticationError(AppError):
    status = 401
    default_message = 'Credenciais inválidas'


class AuthorizationError(AppError):
    status = 403
    default_message = 'Acesso negado'


class NotFoundError(AppError):
    status = 404
    default_message = 'Recurso não encontrado'


class ConflictError(AppError):
    status = 409
    default_message = 'Conflito'


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def _handle_app_error(error):
        return {'error': error.message}, error.status

    @app.errorhandler(404)
    def _handle_404(_error):
        return {'error': 'Recurso não encontrado'}, 404

    @app.errorhandler(405)
    def _handle_405(_error):
        return {'error': 'Método não permitido'}, 405

    @app.errorhandler(Exception)
    def _handle_unexpected(error):
        # Log the real cause with a traceback instead of swallowing it in a bare
        # `except:` and returning a generic message (the old behavior).
        logger.exception('Falha inesperada ao processar a requisição: %s', error)
        return {'error': 'Erro interno'}, 500
