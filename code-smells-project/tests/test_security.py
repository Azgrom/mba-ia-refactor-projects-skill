"""Security checks for the approved findings (F-001..F-005)."""
import sqlite3

import pytest

from loja.config import Config


def test_admin_endpoints_removidos(client):
    # F-001 / F-003: the arbitrary-SQL and reset-db endpoints no longer exist.
    assert client.post("/admin/query", json={"sql": "SELECT 1"}).status_code == 404
    assert client.post("/admin/reset-db").status_code == 404


def test_login_nao_permite_sql_injection(client):
    # F-002: classic auth-bypass payload must fail now (parameterized + hashed).
    r = client.post("/login", json={"email": "joao@email.com", "senha": "' OR '1'='1"})
    assert r.status_code == 401


def test_busca_injection_e_neutralizada(client):
    # Injection in search is treated as a literal, returning no rows rather than all.
    r = client.get("/produtos/busca?q=' OR '1'='1")
    assert r.status_code == 200
    assert r.get_json()["dados"] == []


def test_health_nao_vaza_segredo(client):
    body = client.get("/health").get_json()
    # F-004: secret/debug/db_path removed from the health payload.
    for leaked in ("secret_key", "debug", "db_path"):
        assert leaked not in body
    assert body["status"] == "ok"
    assert body["counts"]["produtos"] == 10


def test_senha_armazenada_com_hash(app, config):
    # F-005: seeded passwords are not stored in plaintext.
    conn = sqlite3.connect(config.db_path)
    row = conn.execute(
        "SELECT senha FROM usuarios WHERE email = 'joao@email.com'"
    ).fetchone()
    conn.close()
    stored = row[0]
    assert stored != "123456"
    assert stored.startswith(("pbkdf2:", "scrypt:", "argon2"))


def test_secret_key_obrigatoria_em_producao():
    # F-004: production refuses to boot without an externally supplied secret.
    with pytest.raises(RuntimeError):
        Config.from_env({"APP_ENV": "production"})


def test_erro_interno_e_sanitizado(app, monkeypatch):
    # F-013: unexpected errors return a generic message, never internal detail.
    from loja.services import ProdutoService

    def boom(self):
        raise RuntimeError("detalhe interno sensível: SELECT * FROM segredo")

    monkeypatch.setattr(ProdutoService, "listar", boom)
    client = app.test_client()
    r = client.get("/produtos")
    assert r.status_code == 500
    assert r.get_json() == {"erro": "Erro interno do servidor"}
    assert "segredo" not in r.get_data(as_text=True)
