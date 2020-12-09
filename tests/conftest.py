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
    app.config["MONGO_CLIENT"] = mongodb
    app.config["MONGO_DATABASE"] = mongodb

    yield app


@pytest.fixture
def client(app):
    """Setup client."""
    return app.test_client()
