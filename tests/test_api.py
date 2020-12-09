"""Test API functionality."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest
from app.api import authenticate_user, conduct_reanalysis, run_rescore
from app.exceptions import PipelineExecutionError, SSHKeyException
from app.io import Family
from connexion.exceptions import OAuthProblem
from fabric import Connection
from invoke.runners import Result


@pytest.fixture()
def init_rerun_func(monkeypatch):
    """Initialize mocks for toggle rerun function."""
    mock_rundata = Mock(return_value=[])
    mock_pedigree = Mock(return_value=Mock(spec=Family))
    mock_runrescore = Mock()
    # mock tempdir context manager
    mock_tempdir = Mock(spec=TemporaryDirectory, return_value="directory")
    mock_tempdir.return_value = Mock(__enter__=mock_tempdir, __exit__=Mock())
    # mock connection context manager
    mock_connection = Mock(spec=Connection)
    mock_context = Mock(spec=Connection)
    mock_connection.return_value = Mock(
        __enter__=mock_context,
        __exit__=Mock(),
    )
    monkeypatch.setattr("app.api.create_rundata_file", mock_rundata)
    monkeypatch.setattr("app.api.create_new_pedigree", mock_pedigree)
    monkeypatch.setattr("app.api.Connection", mock_connection)
    monkeypatch.setattr("app.api.run_rescore", mock_runrescore)

    return mock_connection, mock_context, mock_rundata, mock_pedigree, mock_runrescore


def test_health(client):
    """Test if client can successfully start."""
    response = client.get("/")
    assert response.status_code == 200


def test_authenticate_user(app, monkeypatch):
    """Test that user is correctly authenticated."""

    api_key = "very_secret"
    # patch api key and whitelist emails
    monkeypatch.setitem(app.config, "API_SECRET_KEY", "very_secret")
    monkeypatch.setitem(app.config, "AUTHORIZED_USERS", ["foo@mail.com", "bar@me.com"])

    # success test
    user_email = "foo@mail.com"
    expected = {"sub": user_email, "scope": "super_user"}
    assert expected == authenticate_user(user_email=user_email, api_key="very_secret")

    # wrong api key
    with pytest.raises(OAuthProblem):
        assert expected == authenticate_user(user_email="foo@mail.com", api_key="bad key")

    # wrong email
    with pytest.raises(OAuthProblem):
        assert expected == authenticate_user(user_email="bad_mail@mail.com", api_key="very_secret")


def test_runrescore(app, monkeypatch):
    """Test initiating of new reruns."""
    # mock connection objects
    mock_res = Mock(spec=Result)
    mock_res.failed = False
    mock_res.stdout = "Mock result"
    mock_res.stderr = "Mock result"

    mock_connection = Mock(spec=Connection)
    mock_connection.run.return_value = mock_res

    # patch app functionality
    script_name = "script_name.sh"
    monkeypatch.setitem(app.config, "WORKFLOW_EXEC_SCRIPT", script_name)

    # test invocation
    path = "/some/path.csv"
    run_rescore(mock_connection, Path(path))
    mock_connection.run.assert_called_with(f"{script_name} {path}", warn=True)

    # test response validation of faild command
    mock_res.failed = True
    with pytest.raises(PipelineExecutionError):
        run_rescore(mock_connection, Path(path))


def test_toggle_rerun_success(app, monkeypatch, init_rerun_func):
    """
    Test the API entry point toggle_rerun.

    Core steps
    ==========
    1. Write run data
    2. Write pedigree
    3. Write transfer files
    4. Execute new rerun
    """
    (
        mock_connection,
        mock_context,
        mock_rundata,
        mock_pedigree,
        mock_runrescore,
    ) = init_rerun_func
    # Set mock ssh keys
    test_config = {
        "SSH_KEY_FILENAME": "/path/to/ssh-keys",
        "SSH_PASSPHRASE": "phrase",
        "WORKFLOW_HOST": "http://worker.remote",
        "WORKFLOW_USER": "user",
        "WORKFLOW_DATA_DIR": "/data/dir",
    }
    for var, val in test_config.items():
        monkeypatch.setitem(app.config, var, val)

    # toggle rerun
    case_id = "9075-18"
    sample_ids = ["9075-18", "2112-19"]
    conduct_reanalysis(case_id, sample_ids=sample_ids)

    # test that rundata was written
    mock_rundata.assert_called_with(case_id)
    # test that mock_pedigree
    mock_pedigree.assert_called_with(case_id, sample_ids, [])
    # test setting up connection
    mock_connection.assert_called_with(
        host=test_config["WORKFLOW_HOST"],
        user=test_config["WORKFLOW_USER"],
        connect_kwargs={
            "key_filename": test_config["SSH_KEY_FILENAME"],
            "passphrase": test_config["SSH_PASSPHRASE"],
        },
    )
    # test transfering of files
    assert mock_context.return_value.put.call_count == 2
    # launching rerun on remote
    mock_runrescore.assert_called_once()


def test_toggle_rerun_ssh_key(app, monkeypatch, init_rerun_func):
    """Test the API entry point toggle_rerun ssh key failure."""
    (
        mock_connection,
        mock_context,
        mock_rundata,
        mock_pedigree,
        mock_runrescore,
    ) = init_rerun_func
    # Set mock ssh keys
    monkeypatch.setitem(app.config, "key_filename", None)

    # toggle rerun
    case_id = "9075-18"
    sample_ids = ["9075-18", "2112-19"]

    with pytest.raises(SSHKeyException):
        conduct_reanalysis(case_id, sample_ids=sample_ids)
