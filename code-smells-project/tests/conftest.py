import os
import tempfile

import pytest

from loja import create_app
from loja.config import Config


@pytest.fixture
def config(tmp_path):
    return Config(
        secret_key="test-secret",
        db_path=str(tmp_path / "test.db"),
        debug=False,
        ambiente="producao",
        seed=True,
    )


@pytest.fixture
def app(config):
    application = create_app(config)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()
