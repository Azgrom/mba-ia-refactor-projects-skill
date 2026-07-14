"""Executable entry point.

The application is defined by the ``loja`` package's ``create_app`` factory. ``app`` is
exposed at module level for WSGI servers (e.g. ``gunicorn app:app``). Running this file
directly starts the development server using environment-driven configuration.
"""
from loja import create_app
from loja.config import Config

config = Config.from_env()
app = create_app(config)

if __name__ == "__main__":
    print("=" * 50)
    print("SERVIDOR INICIADO")
    print(f"Rodando em http://{config.host}:{config.port}")
    print("=" * 50)
    app.run(host=config.host, port=config.port, debug=config.debug)
