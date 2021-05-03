"""Shared fixtures."""

import os
import tempfile

import connexion
import pytest
from app.app import create_app

from .config import TestConfig


@pytest.fixture
def app(mongodb):
    """Instanciate testing client."""
    app = create_app(TestConfig)
    # configure test environment
    app.config["MONGO_CLIENT"] = mongodb
    app.config["MONGO_DATABASE"] = mongodb

    test_config = {
        "WORKFLOW_HOST": "http://worker.remote",
        "WORKFLOW_USER": "user",
        "WORKFLOW_DATA_DIR": "/data/dir",
    }
    for var, val in test_config.items():
        app.config[var] = val

    yield app


@pytest.fixture
def client(app):
    """Setup client."""
    return app.test_client()
