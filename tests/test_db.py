"""Test database interactions."""

import pytest
from app.db import CaseNotFoundError, query_case


def test_query_cases(app):
    """Test querying of data."""
    # success
    assert query_case("9075-18")

    # test case not exist
    with pytest.raises(CaseNotFoundError):
        query_case("Not a case_id")
