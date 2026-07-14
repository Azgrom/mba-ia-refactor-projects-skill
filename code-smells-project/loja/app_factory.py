"""Composition root: build config, infrastructure, services, routes, and errors.

Importing this module has no side effects. ``create_app`` is import-safe: it does not
start a server. It does create/seed the configured database so the app is ready to serve.
"""
from __future__ import annotations

import logging

from flask import Flask
from flask_cors import CORS

from .config import Config
from .db import Database
from .errors import register_error_handlers
from .repositories import PedidoRepository, ProdutoRepository, UsuarioRepository
from .routes import build_blueprints
from .services import (
    HealthService,
    Notifier,
    PedidoService,
    ProdutoService,
    RelatorioService,
    UsuarioService,
)


def create_app(config: Config | None = None) -> Flask:
    cfg = config or Config.from_env()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = cfg.secret_key
    app.config["DEBUG"] = cfg.debug
    # Notifications flow through the logger; keep them observable.
    app.logger.setLevel(logging.INFO)

    # No wildcard CORS: only explicitly configured origins are allowed (finding F-004).
    CORS(app, origins=cfg.cors_origins or [])

    db = Database(cfg.db_path)
    db.init(seed=cfg.seed)

    produto_repo = ProdutoRepository(db)
    usuario_repo = UsuarioRepository(db)
    pedido_repo = PedidoRepository(db)
    notifier = Notifier(app.logger)

    services = {
        "produto": ProdutoService(db, produto_repo),
        "usuario": UsuarioService(db, usuario_repo),
        "pedido": PedidoService(db, produto_repo, pedido_repo, notifier),
        "relatorio": RelatorioService(pedido_repo),
        "health": HealthService(produto_repo, usuario_repo, pedido_repo, cfg.ambiente),
    }

    for blueprint in build_blueprints(services):
        app.register_blueprint(blueprint)
    register_error_handlers(app)
    app.teardown_appcontext(db.close)

    return app
