"""Setup and establish a connection to the mongodb."""
import logging

from flask import current_app
from flask.cli import with_appcontext
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

LOG = logging.getLogger(__name__)


class CaseNotFoundError(Exception):
    """Individual id missing in the database."""

    pass


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


def query_case(case_id):
    """Query database for a case."""
    db_client = current_app.config["MONGO_DATABASE"]
    LOG.info(f"Querying db: {db_client} for case: {case_id}")
    resp = db_client.case.find_one({"_id": case_id})

    if resp is None:  # no case id
        msg = f'Case "{case_id}" not found in database'
        LOG.error(msg)
        raise CaseNotFoundError(msg)
    return resp
