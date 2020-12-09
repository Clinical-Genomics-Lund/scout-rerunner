"""Setup application factory."""
import logging
import os
from logging.config import dictConfig
from pathlib import Path

import connexion
import yaml
from flask import Flask, current_app
from flask.cli import current_app, with_appcontext
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .__version__ import __version__ as version

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "wsgi": {
                "class": "logging.StreamHandler",
                "stream": "ext://flask.logging.wsgi_errors_stream",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["wsgi"]},
    }
)

LOG = logging.getLogger(__name__)


def create_app(test_config=None):
    """Create and configure app."""
    logging.basicConfig(level=logging.DEBUG)

    app = connexion.App(__name__, specification_dir="openapi", options={"swagger_ui": True})
    app.add_api("openapi.yaml")

    application = app.app

    # set pymongo config

    with application.app_context():
        if test_config:
            application.config.from_object(test_config)
        else:
            load_config("config.yml")
        init_db()

    @app.route("/")
    def about():
        return f"PEDmaker version: {version}"

    return application


def init_db():
    """Initialize from flask"""
    db_name = current_app.config.get("MONGO_DBNAME", "scout")

    host = current_app.config.get("MONGO_HOST", "localhost")
    port = current_app.config.get("MONGO_PORT", 27017)
    LOG.info(f"Try to connect to database {db_name} at {host}:{port}")
    try:
        client = MongoClient(
            host=host,
            port=port,
            username=current_app.config.get("MONGO_USERNAME", None),
            password=current_app.config.get("MONGO_PASSWORD", None),
            serverSelectionTimeoutMS=current_app.config.get("MONGO_TIMEOUT", 60),
        )
    except ServerSelectionTimeoutError as err:
        LOG.warning("Connection Refused")
        raise ConnectionFailure

    LOG.info("Connection established")

    current_app.config["MONGO_DATABASE"] = client[db_name]
    current_app.config["MONGO_CLIENT"] = client


def load_config(path):
    """Load app config."""
    config_file = "config.yml"
    LOG.info(f"Load configurations from file: {config_file}")
    with open(config_file) as inpt:
        current_app.config.from_mapping(yaml.safe_load(inpt))

    LOG.info("Load configurations from environment variables")
    # get remote authentication information, assumes SSH key setup
    current_app.config["SSH_KEY_FILENAME"] = os.environ.get("SSH_KEY_FILENAME")
    current_app.config["SSH_PASSPHRASE"] = os.environ.get("SSH_PASSPHRASE")
    # get api secret key
    current_app.config["API_SECRET_KEY"] = os.environ.get("API_SECRET_KEY")
