"""IO functions."""
import csv
import logging
from itertools import chain

import attr
import cattr
from flask import current_app as app
from pymongo.errors import InvalidId

from .db import query_case
from .exceptions import IndividualIdNotFoundError, NoSampleIdError

LOG = logging.getLogger(__name__)


SEX_TR = {
    "unknown": 0,
    ".": 0,
    "male": 1,
    "female": 2,
}
PHENOTYPE_TR = {
    "unknown": 0,
    ".": 0,
    "unaffected": 1,
    "affected": 2,
}

# Pedigree types
@attr.s(frozen=True)
class Individual(object):
    id = attr.ib(type=str)
    family_id = attr.ib(type=str)
    mother = attr.ib(type=str, default=0)
    father = attr.ib(type=str, default=0)
    sex = attr.ib(type=int, default=0, converter=int)
    phenotype = attr.ib(type=int, default=0, converter=int)

    @sex.validator
    @phenotype.validator
    def check_categories(self, attribute, value):
        """
        Check encoding of categories

        Valid entries are.
        """
        if not 0 <= value <= 2:
            raise ValueError("Categories must be either of 0, 1 and 2.")


@attr.s()
class Family(object):
    """Family container."""

    family_id = attr.ib(type=str)
    # fixed variables
    _individuals = tuple()
    ped_header = [
        "#FamilyID",
        "IndividualID",
        "PaternalID",
        "MaternalID",
        "Sex",
        "Phenotype",
    ]

    def add_individual(self, individual: Individual) -> None:
        """Add individuals to family."""
        if not isinstance(individual, (Individual)):
            raise ValueError("Individual must be a {type(Individual).__name__} object")
        self._individuals = tuple(chain(self._individuals, [individual]))

    def to_ped(self, output, write_header=True) -> None:
        """To pedigree file."""
        cwriter = csv.DictWriter(output, fieldnames=self.ped_header, delimiter="\t")
        if write_header:
            cwriter.writeheader()
        for row in self._individuals:
            cwriter.writerow(
                {
                    self.ped_header[0]: row.id,
                    self.ped_header[1]: row.family_id,
                    self.ped_header[2]: row.mother,
                    self.ped_header[3]: row.father,
                    self.ped_header[4]: row.sex,
                    self.ped_header[5]: row.phenotype,
                }
            )

    def to_json(self) -> None:
        """Convert attr to json."""
        return cattr.unstructure(self._individuals)


def create_new_pedigree(case_id, sample_ids, edited_sample_info=[]):
    """Make new pedigree."""
    resp = query_case(case_id)

    if not isinstance(sample_ids, (list, tuple)):
        raise ValueError("Sample ids must have the following format [<id_1>, <id_2>]")

    if len(sample_ids) == 0:  # no sample was included
        LOG.warning(f"No sample id specified to be included for case: {case_id}")
        raise NoSampleIdError("No sample id was given, cannot be empty.")

    # index edited_sample_info
    edited_metadata = {mod_data["sample_id"]: mod_data for mod_data in edited_sample_info}

    # filter individuals
    individuals = {
        ind["individual_id"]: ind
        for ind in resp["individuals"]
        if ind["individual_id"] in sample_ids
    }
    missing_ind = set(sample_ids) - set(individuals)
    if len(missing_ind) != 0:
        LOG.error("Missing individual ids: {}".format(", ".join(missing_ind)))
        raise IndividualIdNotFoundError(missing_ind)

    # create PED object
    family_ped = Family(family_id=case_id)
    for ind_id, individual in individuals.items():
        mod_data = edited_metadata.get(ind_id, {})  # get modified data
        # exclude familiy information for samples not selected
        mother = individual["mother"] if individual["mother"] in individuals else 0
        father = individual["father"] if individual["father"] in individuals else 0

        # set original values
        org_sex = SEX_TR.get(individual["sex"], 0)
        sex = mod_data.get("sex", org_sex)
        org_phenotype = PHENOTYPE_TR.get(individual["phenotype"], 0)
        phenotype = mod_data.get("phenotype", org_phenotype)

        # store family information
        family_ped.add_individual(
            Individual(
                ind_id,
                family_id=case_id,
                mother=mother,
                father=father,
                sex=sex,
                phenotype=phenotype,
            )
        )
    return family_ped


def create_rundata(case_id):
    """Create rundata informaiton."""
    resp = query_case(case_id)
    data_files = {
        "group": case_id,
        "assay": "rescore-dry"
        if app.config["TESTING"]
        else "rescore",  # triggers correct nexflow parameter
        "vcf_snv": resp["vcf_files"]["vcf_snv"],
        "vcf_sv": resp["vcf_files"]["vcf_sv"],
        "vcf_str": resp["vcf_files"]["vcf_str"],
    }
    return [data_files]


def create_rundata_file(path, case_id):
    """Create rundata file."""
    with open(path, "w") as out:
        LOG.info(f"Writing rundata to {path}")
        cwriter = csv.DictWriter(out, fieldnames=list(run_data[0].keys()))
        cwriter.writeheader()
        for row in run_data:
            cwriter.writerow(row)
