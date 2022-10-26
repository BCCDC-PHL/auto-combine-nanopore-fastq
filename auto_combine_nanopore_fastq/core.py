import datetime
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import uuid

from typing import Iterator, Optional

import auto_combine_nanopore_fastq.samplesheet as ss


def find_fastq_dirs(config, check_symlinks_complete=True):
    gridion_run_id_regex = "\d{8}_\d{4}_X[1-5]_[A-Z0-9]+_[a-z0-9]{8}"

    run_parent_dirs = config['run_parent_dirs']
    for run_parent_dir in run_parent_dirs:
        run_dirs = os.scandir(run_parent_dir)
        
        for run_dir in run_dirs:
            run_id = run_dir.name
            analysis_outdir = os.path.abspath(os.path.join(run_dir, "fastq_pass_combined"))
            matches_gridion_run_id_regex = re.match(gridion_run_id_regex, run_id)
            if config['check_upload_complete']:
                ready_to_analyze = os.path.exists(os.path.join(run_dir.path, "upload_complete.json"))
            else:
                ready_to_analyze = True
            samplesheets_found = glob.glob(os.path.join(run_dir, "SampleSheet*.csv")) + glob.glob(os.path.join(run_dir, "sample_sheet*.csv"))
            samplesheet_to_parse = ss.choose_samplesheet_to_parse(samplesheets_found)
            fastq_pass_dir = os.path.abspath(os.path.join(run_dir.path, "fastq_pass"))
            has_fastq_pass_dir = os.path.exists(fastq_pass_dir) and os.path.isdir(fastq_pass_dir) 
            analysis_not_already_initiated = not os.path.exists(analysis_outdir)
            conditions_checked = {
                "is_directory": run_dir.is_dir(),
                "matches_gridion_run_id_format": matches_gridion_run_id_regex is not None,
                "ready_to_analyze": ready_to_analyze,
                "has_fastq_pass_dir": has_fastq_pass_dir,
                "analysis_not_already_initiated": analysis_not_already_initiated,
                "samplesheet_exists": (samplesheet_to_parse is not None) and (os.path.exists(samplesheet_to_parse)),
            }
            conditions_met = list(conditions_checked.values())
            analysis_parameters = {}
            if all(conditions_met):
                logging.info(json.dumps({"event_type": "fastq_directory_found", "sequencing_run_id": run_id, "run_directory": os.path.abspath(run_dir.path)}))
                analysis_parameters['run_id'] = run_id
                analysis_parameters['run_dir'] = os.path.abspath(run_dir.path)
                analysis_parameters['fastq_input'] = os.path.abspath(os.path.join(run_dir.path, "fastq_pass"))
                analysis_parameters['samplesheet'] = samplesheet_to_parse
                analysis_parameters['outdir'] = analysis_outdir
                yield analysis_parameters
            else:
                logging.debug(json.dumps({"event_type": "directory_skipped", "run_directory": os.path.abspath(run_dir.path), "conditions_checked": conditions_checked}))
                yield None
    

def scan(config: dict[str, object]) -> Iterator[Optional[dict[str, object]]]:
    """
    Scanning involves looking for all existing runs and storing them to the database,
    then looking for all existing symlinks and storing them to the database.
    At the end of a scan, we should be able to determine which (if any) symlinks need to be created.

    :param config: Application config.
    :type config: dict[str, object]
    :return: A run directory to analyze, or None
    :rtype: Iterator[Optional[dict[str, object]]]
    """
    logging.info(json.dumps({"event_type": "scan_start"}))
    for symlinks_dir in find_fastq_dirs(config):    
        yield symlinks_dir


def analyze_run(config, run):
    """
    Initiate an analysis on one directory of fastq files.
    """
    samplesheet_by_barcode = ss.parse_samplesheet(run['samplesheet'])
    sequencing_run_id = run['run_id']
    run_dir = run['run_dir']
    analysis_command = []
    logging.info(json.dumps({"event_type": "analysis_started", "sequencing_run_id": sequencing_run_id}))
    
    os.makedirs(os.path.join(run_dir, "fastq_pass_combined"))
    combine_fastq_complete = {'num_barcodes_processed': 0}
    for barcode_num in samplesheet_by_barcode:
        barcode_num_padded = barcode_num.zfill(2)
        barcode_fastq_path = os.path.join(run_dir, 'fastq_pass', 'barcode' + barcode_num_padded)
        input_fastqs = glob.glob(os.path.join(barcode_fastq_path, '*.fastq.gz'))
        sample_id = samplesheet_by_barcode[barcode_num]['sample_id']
        output_fastq_path = os.path.join(run_dir, 'fastq_pass_combined', sample_id + '_barcode' + barcode_num_padded + '_RL.fastq.gz')
        out_fh = open(output_fastq_path, 'wb')
        for fastq in input_fastqs:
            in_fh = open(fastq, 'rb')
            shutil.copyfileobj(in_fh, out_fh)
            in_fh.close()
        out_fh.close()
        combine_fastq_complete['num_barcodes_processed'] += 1

    combine_fastq_complete['timestamp'] = datetime.datetime.now().isoformat()
    with open(os.path.join(run_dir, 'combine_fastq_complete.json'), 'w') as f:
        f.write(json.dumps(combine_fastq_complete, indent=2) + '\n')

    os.system('chmod ' + str(config['combined_fastq_permissions']) + ' ' + os.path.join(run_dir, 'fastq_pass_combined') + '/*.fastq.gz')
    os.chmod(os.path.join(run_dir, 'fastq_pass_combined'), 0o550)

    logging.info(json.dumps({"event_type": "combine_fastq_completed", "sequencing_run_id": sequencing_run_id}))
    
    
