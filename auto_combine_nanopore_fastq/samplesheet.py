import csv
import os
import re

from typing import Optional

def choose_samplesheet_to_parse(samplesheet_paths: list[str]) -> Optional[str]:
    """
    Choose which samplesheet to parse. If a 'custom' samplesheet is present, choose it.
    Otherwise, choose the 'standard' samplesheet'.

    :param samplesheet_paths:
    :type samplesheet_paths: list[str]
    """
    # TODO: better logic for choosing samplesheet?
    samplesheet_to_parse = None
    if len(samplesheet_paths) == 1:
        samplesheet_to_parse = os.path.abspath(samplesheet_paths[0])
    elif len(samplesheet_paths) > 0:
        standard_samplesheets = list(filter(lambda x: os.path.basename(x).startswith('sample_sheet'), samplesheet_paths))
        custom_samplesheets = list(filter(lambda x: os.path.basename(x).startswith('SampleSheet'), samplesheet_paths))
        if len(custom_samplesheets) > 0:
            samplesheet_to_parse = custom_samplesheets[0]
        elif len(standard_samplesheets) > 0:
            samplesheet_to_parse = standard_samplesheets[0]

    return samplesheet_to_parse


def parse_samplesheet(samplesheet_path):
    samplesheet_by_barcode = {}
    with open(samplesheet_path, 'r') as f:
        reader = csv.DictReader(f, dialect='unix')
        for row in reader:
            samplesheet_by_barcode[row['barcode']] = row

    return samplesheet_by_barcode
