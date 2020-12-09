"""Exceptions."""


class IndividualIdNotFoundError(Exception):
    """Individual id missing in the database."""

    pass


class NoSampleIdError(Exception):
    """Individual id missing in the database."""

    pass


class PipelineExecutionError(Exception):
    """Error duing execution of pipeline."""

    pass


class SSHKeyException(Exception):
    """Error with the SSH keys on the server."""

    pass
