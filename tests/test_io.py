"""Test io operations."""

from csv import DictWriter
from unittest.mock import Mock, mock_open, patch

import pytest
from app.io import create_new_pedigree, create_rundata


def test_create_rundata(app, monkeypatch):
    """Test if rundata was parsed correctly."""
    # setup data
    case_id = "9075-18"
    dta = create_rundata(case_id)[0]

    # assert correct headers
    headers = list(dta)
    header_colnames = ["group", "assay", "vcf_snv", "vcf_sv", "vcf_str"]
    assert headers == header_colnames

    # check header
    assert dta["group"] == case_id

    # check extraction of vcf
    assert all(dta[vcf].endswith("vcf.gz") for vcf in header_colnames[2:])


def test_assay_definition(app, monkeypatch):
    # check valid assays name when testing and not
    case_id = "9075-18"
    dta = create_rundata(case_id)[0]

    # in testing environment
    assert dta["assay"] == "rescore-dry"

    # wo testing
    monkeypatch.setitem(app.config, "TESTING", False)
    dta = create_rundata(case_id)[0]
    assert dta["assay"] == "rescore"


def test_create_pedigree(app):
    """Test create a new pedigree without additional filtering."""
    case_id = "9075-18"

    # create new pedigree
    exp_id = ["9075-18", "2112-19", "2113-19"]
    ped = create_new_pedigree(case_id, exp_id, {}).to_json()

    # te st file
    assert len(ped) == 3
    assert sorted([sample["id"] for sample in ped]) == sorted(exp_id)


@pytest.mark.parametrize(
    "sample_id",
    [
        (["9075-18"]),
        (["9075-18", "2112-19"]),
        (["9075-18", "2112-19", "2113-19"]),
    ],
)
def test_pedigree_sample_id_filters(app, sample_id):
    """Test create pedigree with variable number of samples."""
    case_id = "9075-18"

    # test one sample
    ped = create_new_pedigree(case_id, sample_id).to_json()
    assert sorted([sample["id"] for sample in ped]) == sorted(sample_id)


EXP_MOD_SEX_TO_FEMALE = (
    {
        "family_id": "9075-18",
        "id": "9075-18",
        "sex": 2,
        "phenotype": 2,
        "mother": 0,
        "father": 0,
    },
)
EXP_MOD_SEX_TO_UNKNOWN = (
    {
        "family_id": "9075-18",
        "id": "9075-18",
        "sex": 0,
        "phenotype": 2,
        "mother": 0,
        "father": 0,
    },
)
EXP_MOD_SEX_TO_UNKNOWN = (
    {
        "family_id": "9075-18",
        "id": "9075-18",
        "sex": 0,
        "phenotype": 2,
        "mother": 0,
        "father": 0,
    },
)
EXP_MOD_SEX_TO_UNKNOWN = (
    {
        "family_id": "9075-18",
        "id": "9075-18",
        "sex": 0,
        "phenotype": 2,
        "mother": 0,
        "father": 0,
    },
)
EXP_MOD_PHEN_TO_AFFECTED = (
    {
        "family_id": "9075-18",
        "id": "9075-18",
        "sex": 1,
        "phenotype": 2,
        "mother": 0,
        "father": 0,
    },
)
EXP_MOD_PHEN_TO_UNKNOWN = (
    {
        "family_id": "9075-18",
        "id": "9075-18",
        "sex": 1,
        "phenotype": 0,
        "mother": 0,
        "father": 0,
    },
)


@pytest.mark.parametrize(
    "edited_data,exp_ped",
    (
        ({"sex": "2"}, EXP_MOD_SEX_TO_FEMALE),
        ({"sex": "0"}, EXP_MOD_SEX_TO_UNKNOWN),
        pytest.param(
            {"sex": "-1"},  # invalid modification
            EXP_MOD_SEX_TO_UNKNOWN,
            marks=pytest.mark.xfail,
        ),
        pytest.param(
            {"sex": "4"},  # invalid modification
            EXP_MOD_SEX_TO_UNKNOWN,
            marks=pytest.mark.xfail,
        ),
        ({"phenotype": "2"}, EXP_MOD_PHEN_TO_AFFECTED),
        ({"phenotype": "0"}, EXP_MOD_PHEN_TO_UNKNOWN),
        pytest.param(
            {"phenotype": "-1"},  # invalid modification
            EXP_MOD_PHEN_TO_UNKNOWN,
            marks=pytest.mark.xfail,
        ),
        pytest.param(
            {"phenotype": "4"},  # invalid modification
            EXP_MOD_PHEN_TO_UNKNOWN,
            marks=pytest.mark.xfail,
        ),
    ),
)
def test_modify_pedigree_data(app, edited_data, exp_ped):
    """Test modification of the pedigree data."""
    case_id = exp_ped[0]["family_id"]
    sample_id = exp_ped[0]["id"]
    edited_data["sample_id"] = sample_id
    ped = create_new_pedigree(case_id, [sample_id], [edited_data])
    assert ped.to_json() == exp_ped


def test_to_ped(app, monkeypatch):
    """Test writing ped files."""
    open_mock = mock_open()
    mock_dictwriter = Mock(spec=DictWriter)
    mock_dictwriter.writeheader = Mock()
    mock_dictwriter.writerow = Mock()

    # mock dictwriter
    monkeypatch.setattr("app.io.csv.DictWriter", mock_dictwriter)
    ped = create_new_pedigree("9075-18", ["9075-18"])
    # call mock
    with open_mock() as o:
        ped.to_ped(o)

    # test header has been written
    mock_dictwriter.return_value.writeheader.assert_called_once()
    # test that rows were written
    mock_dictwriter.return_value.writerow.assert_called()
    # wrote one row
    assert mock_dictwriter.return_value.writerow.call_count == 1
    mock_dictwriter.reset_mock()  # reset mock

    # with two sample ids
    ped = create_new_pedigree("9075-18", ["9075-18", "2112-19"])
    # call mock
    with open_mock() as o:
        ped.to_ped(o, write_header=False)

    # header not written
    mock_dictwriter.return_value.writeheader.assert_not_called()
    mock_dictwriter.return_value.writerow.assert_called()
    # wrote two rows
    assert mock_dictwriter.return_value.writerow.call_count == 2
