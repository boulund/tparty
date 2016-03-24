#!/usr/bin/env python3
# Upload TTT proteotyping pipeline results to Google Docs spreadsheet
# Fredrik Boulund 2016
# Requires python packages:
#   oauth2 
#   oauth2client==1.5.2

from sys import argv, exit
from os.path import getmtime
from datetime import datetime
from collections import namedtuple
from oauth2client.client import SignedJwtAssertionCredentials
import logging
import argparse
import gspread
import json


def parse_commandline(argv):
    """
    Parse command line arguments.
    """

    desc = """Submit TTT proteotyping pipeline results summary to 
    Google Docs spreadsheet. 
    Requires an OAuth2 credentials token in JSON format from Google 
    Developers Console!
    Assumes being run in TTT proteotyping pipeline base dir.
    Fredrik Boulund 2016"""

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("PID", 
            nargs="+",
            help="Proteomics ID (PID) / sample name to report.")
    parser.add_argument("--tokenfile",
            default="/storage/TTT/code/TTT_proteotyping_pipeline/google_token.json",
            required=True,
            metavar="TOKENFILE",
            help="Path to OAuth2 authentication token file.")
    parser.add_argument("--loglevel", 
            dest="loglevel",
            default="INFO",
            choices=["INFO", "DEBUG", "VERBOSE"],
            help="Set logging level.")
    parser.add_argument("--logfile",
            dest="logfile",
            metavar="LOGFILE",
            help="Write log to LOGFILE.")

    if len(argv) < 2:
        parser.print_help()
        exit()
    
    options = parser.parse_args()

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("oauth2client").setLevel(logging.WARNING)
    if options.loglevel == "DEBUG":
        loglevel = logging.DEBUG
    elif options.loglevel == "VERBOSE":
        loglevel = logging.DEBUG
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("oauth2client").setLevel(logging.DEBUG)
    else:
        loglevel = logging.INFO
    if options.logfile:
        logging.basicConfig(filename=options.logfile, level=loglevel)
    else:
        logging.basicConfig(level=loglevel)

    return options



def get_count_proteins(filename):
    """
    Get the number of unique proteins from unique_proteins output.
    """
    with open(filename) as f:
        line = f.readline()
        if line.startswith("Found"):
            count = int(line.split()[1])
        else:
            count = -1
    return count

def count_num_peps(filename):
    """
    Count the number of peptide sequences in FASTA file.
    """
    with open(filename) as f:
        counter = 0
        for line in f:
            if line.startswith(">"):
                counter += 1
    return counter

def count_disc_peps(filename, rank="species"):
    """
    Count the number of discriminative peptides at specified rank.
    """
    with open(filename) as f:
        disc_peps = 0
        for line in f:
            if line.split()[1] == rank:
                disc_peps += 1
    return disc_peps


def get_summary_results(pid):
    """
    Retrieve summary results for Google Docs spreadsheet.

    Assumes workdir is the TTT proteotyping pipeline base dir,
    with output files in the following folders:
    ./3.fasta/
    ./5.results/<pid>/

    Returns a namedtuple with the following fields:
      pid
      bacterial_proteins
      human_proteins
      num_peps
      disc_peps
      completion_date
    """ 

    Results = namedtuple("Results", ["pid", "bacterial_proteins", 
            "human_proteins", "num_peps", "disc_peps", "completion_date"])

    resultsdir_base = "5.results/"+pid+"/"+pid
    taxcomp_filename = resultsdir_base + ".taxonomic_composition.txt"
    bacterial_proteins_filename = resultsdir_base + ".unique_bacterial_proteins.txt"
    human_proteins_filename = resultsdir_base + ".unique_human_proteins.txt"
    disc_peps_filename = resultsdir_base + ".discriminative_peptides.txt"
    num_peps_filename = "3.fasta/" + pid + ".bacterial.fasta"

    bacterial_proteins = get_count_proteins(bacterial_proteins_filename)
    logging.debug("Got %s bacterial proteins from %s", bacterial_proteins, bacterial_proteins_filename)

    human_proteins = get_count_proteins(human_proteins_filename)
    logging.debug("Got %s human proteins from %s", human_proteins, human_proteins_filename)

    num_peps = count_num_peps("3.fasta/"+pid+".bacterial.fasta")
    logging.debug("Counted %s peptides in %s", num_peps, num_peps_filename)

    disc_peps = count_disc_peps(resultsdir_base+".discriminative_peptides.txt")
    logging.debug("Got %s discriminative peptides from %s", disc_peps, disc_peps_filename)

    completion_date = datetime.fromtimestamp(getmtime(taxcomp_filename))
    logging.debug("Got completion date %s for %s", completion_date, taxcomp_filename)

    results = Results(pid, bacterial_proteins, human_proteins, num_peps, disc_peps, completion_date)
    return results


def report_to_gdoc(results, tokenfile, spreadsheet="TTT proteotyping pipeline results"):
    """
    Upload TTT proteotyping pipeline results to Google Docs spreadsheet.
    
    Connects to Google docs using the 'gspread' Python package. 
    Authentication via OAuth2 credentials from Google Developers Console.

    Relies on some hardcoded column names.
    """
    
    json_key = json.load(open(options.tokenfile))
    scope = ["https://spreadsheets.google.com/feeds"]

    logging.debug("Signing in to Google account %s\n  with credentials from %s", 
            json_key["client_email"], options.tokenfile)
    credentials = SignedJwtAssertionCredentials(json_key['client_email'], 
                                                json_key['private_key'].encode(), 
                                                scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(spreadsheet).sheet1

    # Define the numerical indices to columns in the spreadsheet
    columns = {"EU": 1, 
               "PID": 2, 
               "Proteomics Notes": 3, 
               "Species": 4, 
               "Bacterial proteins": 5, 
               "Human proteins": 6, 
               "Identified spectra/peptides": 7, 
               "Discriminative peptides (species)": 8, 
               "Completion date": 9,
               "Mixing Ratio": 10, 
               "Notes": 11}

    for pid in results:
        try:
            pid_cell = wks.find(pid.pid)
        except gspread.exceptions.CellNotFound:
            logging.warning("Could not find cell for PID: %s", pid.pid)
            continue
        row = pid_cell.row
        wks.update_cell(row, columns["Bacterial proteins"], pid.bacterial_proteins)
        wks.update_cell(row, columns["Human proteins"], pid.human_proteins)
        wks.update_cell(row, columns["Identified spectra/peptides"], pid.num_peps)
        wks.update_cell(row, columns["Discriminative peptides (species)"], pid.disc_peps)
        wks.update_cell(row, columns["Completion date"], pid.completion_date)


if __name__ == "__main__":
    options = parse_commandline(argv)
    results = [get_summary_results(pid) for pid in options.PID]
    report_to_gdoc(results, options.tokenfile)
