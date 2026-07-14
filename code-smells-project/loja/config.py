"""Configuration: read environment once, normalize types, fail closed on required secrets."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field

APP_VERSION = "1.0.0"


@dataclass(frozen=True)
class Config:
    secret_key: str
    db_path: str = "loja.db"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 5000
    ambiente: str = "producao"
    seed: bool = True
    # Cross-origin: empty list means no cross-origin access is granted (no wildcard).
    cors_origins: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Config":
        env = os.environ if env is None else env
        ambiente = env.get("APP_ENV", "development")
        is_prod = ambiente == "production"

        secret = env.get("SECRET_KEY")
        if not secret:
            if is_prod:
                raise RuntimeError(
                    "SECRET_KEY is required when APP_ENV=production and must not be hardcoded."
                )
            # Development convenience only: ephemeral per-process key, never committed.
            secret = secrets.token_urlsafe(32)

        debug = env.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes") or (
            not is_prod and env.get("FLASK_DEBUG") is None and ambiente == "development"
        )
        # Default debug OFF unless explicitly running the development profile.
        if is_prod:
            debug = False

        origins = [o.strip() for o in env.get("CORS_ORIGINS", "").split(",") if o.strip()]

        return cls(
            secret_key=secret,
            db_path=env.get("DB_PATH", "loja.db"),
            debug=debug,
            host=env.get("HOST", "127.0.0.1"),
            port=int(env.get("PORT", "5000")),
            ambiente="producao" if is_prod else env.get("HEALTH_AMBIENTE", "producao"),
            seed=env.get("SEED", "true").lower() != "false",
            cors_origins=origins,
        )
