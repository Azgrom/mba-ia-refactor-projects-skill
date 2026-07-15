"""Database lifecycle: request-scoped SQLite connections and an explicit unit of work.

Replaces the process-global connection (finding F-009). Each request gets its own
connection stored on ``flask.g`` and closed on teardown; schema creation and seeding
are an explicit startup step, not a side effect of the first query.
"""
from __future__ import annotations

import sqlite3
from contextlib import closing, contextmanager

from flask import g
from werkzeug.security import generate_password_hash

_G_KEY = "loja_db_conn"

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT 'pendente',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
]

SEED_PRODUTOS = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# Seed credentials are hashed at rest (finding F-005); the plaintext here is only the
# development login secret, hashed before storage so these seed logins still work.
SEED_USUARIOS = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self) -> sqlite3.Connection:
        """Return the connection bound to the current request context."""
        conn = getattr(g, _G_KEY, None)
        if conn is None:
            conn = self.connect()
            setattr(g, _G_KEY, conn)
        return conn

    def close(self, _exc=None) -> None:
        conn = getattr(g, _G_KEY, None)
        if conn is not None:
            conn.close()
            setattr(g, _G_KEY, None)

    @contextmanager
    def transaction(self):
        """One atomic unit of work: commit on success, roll back on any failure."""
        conn = self.get()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def init(self, seed: bool = True) -> None:
        """Create schema and (optionally) seed. Explicit startup step, idempotent."""
        with closing(self.connect()) as conn:
            cursor = conn.cursor()
            for statement in SCHEMA:
                cursor.execute(statement)
            conn.commit()
            if seed:
                cursor.execute("SELECT COUNT(*) FROM produtos")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany(
                        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
                        " VALUES (?, ?, ?, ?, ?)",
                        SEED_PRODUTOS,
                    )
                    cursor.executemany(
                        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                        [
                            (nome, email, generate_password_hash(senha), tipo)
                            for nome, email, senha, tipo in SEED_USUARIOS
                        ],
                    )
                    conn.commit()
