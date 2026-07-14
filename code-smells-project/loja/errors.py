"""Typed application errors and a single sanitized HTTP mapping.

Client errors keep the legacy ``{"erro": <mensagem>}`` shape (optionally with the
legacy ``sucesso: false`` flag) so the existing 4xx contract is preserved. Unexpected
failures are mapped to a generic 500 that never leaks internal detail.
"""
from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    """Base for expected, client-facing failures with a safe message."""

    status = 400

    def __init__(self, message: str, status: int | None = None, flag: bool = False):
        super().__init__(message)
        self.message = message
        if status is not None:
            self.status = status
        # ``flag`` reproduces the legacy responses that also carried ``sucesso: false``.
        self.flag = flag

    def body(self) -> dict:
        payload = {"erro": self.message}
        if self.flag:
            payload["sucesso"] = False
        return payload


class ValidationError(AppError):
    status = 400


class NotFoundError(AppError):
    status = 404


class ConflictError(AppError):
    status = 409


class AuthError(AppError):
    status = 401


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _handle_app_error(error: AppError):
        return jsonify(error.body()), error.status

    @app.errorhandler(HTTPException)
    def _handle_http_exception(error: HTTPException):
        # Preserve framework HTTP semantics (e.g. 404 for unknown routes, 405).
        return error

    @app.errorhandler(Exception)
    def _handle_unexpected(error: Exception):
        # Log the real cause server-side; never return it to the client.
        app.logger.exception("unexpected request failure")
        return jsonify({"erro": "Erro interno do servidor"}), 500
