"""API interface."""
import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import connexion
from connexion.exceptions import OAuthProblem
from fabric import Connection
from flask import current_app as app
from flask import request
from paramiko.ssh_exception import SSHException

from .db import CaseNotFoundError
from .exceptions import PipelineExecutionError, SSHKeyException
from .io import IndividualIdNotFoundError, create_new_pedigree, create_rundata_file

LOG = logging.getLogger(__name__)


def authenticate_user(user_email, api_key, required_scopes=None):
    """Authenticate API keys."""
    LOG.info(f"recieving login atempt; {user_email}; passwd: {api_key}")
    if not api_key == app.config["API_SECRET_KEY"]:
        LOG.error(
            f'Error passwd "{api_key}" not matching expected "{app.config["API_SECRET_KEY"]}"'
        )
        raise OAuthProblem()
    authorized_users = app.config["AUTHORIZED_USERS"]
    LOG.info(f"loading list of authorized users: {authorized_users}")
    if not user_email in authorized_users:
        LOG.error(f"{user_email} not in {authorized_users}")
        raise OAuthProblem()

    info = {"sub": user_email, "scope": "super_user"}

    # validate scopes
    if required_scopes is not None and not validate_scope(required_scopes, info["scope"]):
        raise OAuthScopeProblem(
            description="Provided user doesn't have the equired access rights",
            required_scopes=required_scopes,
            token_scopes=info["scope"],
        )

    return info


def conduct_reanalysis(case_id, **kwargs):
    """Setup and start a reanalysis."""
    LOG.info(f"Recieved request; case id: {case_id}; {kwargs}")
    pedigree = create_new_pedigree(case_id, kwargs.get("sample_ids", []), kwargs.get("body", []))

    cnf = app.config
    # write files to temporary directory
    with TemporaryDirectory(prefix=case_id) as tmp_dir:
        date = datetime.now().strftime("%y%m%d_%H%M%S")
        directory = Path(tmp_dir)
        base_fname = f"{case_id}_{date}_rescore"
        # write run data to csv format
        run_data_path = directory / f"{base_fname}.csv"
        run_data = create_rundata_file(case_id)
        # write pedigree file
        ped_path = directory / f"{base_fname}.ped"
        LOG.info(f"Writing pedigree to {ped_path}")
        with open(ped_path, "w") as out:
            pedigree.to_ped(out, write_header=False)
        # set up ssh options and connect to remote
        kwargs = {
            "passphrase": cnf.get("SSH_PASSPHRASE"),
            "key_filename": cnf.get("SSH_KEY_FILENAME"),
        }
        if kwargs["key_filename"] is None and os.environ.get("SSH_AGENT_PID") is None:
            raise SSHKeyException("No SSH key specified.")

        # setup connection
        host = cnf["WORKFLOW_HOST"]
        user = cnf["WORKFLOW_USER"]
        LOG.info(f"Connecting to remote: {user}@{host}")
        with Connection(host=host, user=user, connect_kwargs=kwargs) as conn:
            # transfer files
            remote_data = cnf["WORKFLOW_DATA_DIR"]
            LOG.debug(f"SCP {run_data_path.absolute()} {remote_data}")
            conn.put(str(run_data_path.absolute()), remote=remote_data)
            conn.put(str(ped_path.absolute()), remote=remote_data)
            run_rescore(conn, Path(remote_data).joinpath(run_data_path.name))  # start rerun


def rerun_wrapper(case_id, **kwargs):
    """API entrypoint wrapper with return code."""
    try:
        conduct_reanalysis(case_id, **kwargs)
    except (
        CaseNotFoundError,
        IndividualIdNotFoundError,
    ) as err:  # if case_id was not in database
        return str(err), 404
    except PipelineExecutionError as err:  # Pipeline execution crashed
        msg = f"{type(err).__name__} - {str(err)}"
        LOG.error(msg)
        msg = "There was an error when executing the pipeline, please contact administrator"
        return msg, 500
    except SSHKeyException as err:  # Credentials error
        msg = f"{type(err).__name__} - {str(err)}"
        LOG.error(msg)
        msg = "There was an error with the connection to the remote server, please contact administrator"
        raise
        return msg, 500
    except Exception as err:  # generic data
        # clean up data
        msg = f"{type(err).__name__} - {str(err)}"
        LOG.error(msg)
        return msg, 500  # fail

    return 204


def run_rescore(connection, run_data_path):
    """Run the rescore nextflow analysis."""
    cmd = " ".join(
        [
            app.config["WORKFLOW_EXEC_SCRIPT"],
            str(run_data_path.absolute()),  # csv file path
        ]
    )
    LOG.info(f"Executing cmd on {connection.host}: {cmd}")
    resp = connection.run(cmd, warn=True)
    LOG.debug(f"Run output: {resp.stdout.strip()}")
    if resp.failed:
        raise PipelineExecutionError(
            {
                "cmd": cmd,
                "stdout": resp.stdout.strip(),
                "stderr": resp.stderr.strip(),
            }
        )
