#!/usr/bin/env python3.5
# encoding: utf-8
#
#  ---------------------------------------------------------- 
#  This file is part of TPARTY: http://tparty.readthedocs.org
#  ---------------------------------------------------------- 
#
#  Copyright (c) 2016, Fredrik Boulund <fredrik.boulund@chalmers.se>
#  
#  Permission to use, copy, modify, and/or distribute this software for any
#  purpose with or without fee is hereby granted, provided that the above
#  copyright notice and this permission notice appear in all copies.
#  
#  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
#  REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
#  FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
#  INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
#  LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
#  OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
#  PERFORMANCE OF THIS SOFTWARE.

from sys import argv, exit
from os.path import getmtime
from os import listdir
from datetime import datetime
from collections import namedtuple
from oauth2client.client import SignedJwtAssertionCredentials
from xml.etree import ElementTree
import yaml
import platform
import logging
import argparse
import gspread
import json
import sqlite3


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
    parser.add_argument("-t", "--tokenfile", dest="tokenfile",
            default="/storage/TTT/code/google_token.json",
            required=True,
            metavar="TOKENFILE",
            help="Path to OAuth2 authentication token file.")
    parser.add_argument("-s", "--snakemake-configfile", dest="snakemake_configfile",
            required=True,
            help="Path to Snakemake configfile.")
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
    
    logging.info("Running with the following settings:")
    for option, value in vars(options).items():
        logging.info("%s\t%s", option, value)

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



def get_xtandem_db_version(xmlfile, taxon="bacteria"):
    """
    Get X!Tandem db version (date).
    """
    tree = ElementTree.parse(xmlfile)
    root = tree.getroot()
    xtandem_db = root.findall("taxon[@label='{taxon}']/file".format(taxon=taxon))[0].attrib["URL"]
    modification_date = datetime.fromtimestamp(getmtime(xtandem_db)).strftime("%Y-%m-%d")
    return modification_date


def get_genome_db_version(genome_db):
    """
    Get genome db version (date).
    """

    modification_date = datetime.fromtimestamp((getmtime(genome_db))).strftime("%Y-%m-%d")
    return modification_date


def get_taxref_db_version(taxref_db):
    """
    Get taxref db version (from SQL database comment), and number of refseqs.
    """

    db = sqlite3.connect(taxref_db)
    version = db.execute("SELECT * FROM version").fetchone()[0]
    refseqs = db.execute("SELECT Count(*) FROM refseqs").fetchone()[0]
    return (version, refseqs)


def get_annotation_db_version(annotation_db):
    """
    Get annotation db version (modification date and number of annotations from SQL database).
    """

    db = sqlite3.connect(annotation_db)
    modification_date = datetime.fromtimestamp((getmtime(annotation_db))).strftime("%Y-%m-%d")
    annotations = db.execute("SELECT Count(*) FROM annotations").fetchone()[0]
    return (modification_date, annotations)



def get_database_versions(snakemake_configfile):
    """
    Parse Snakemake YAML configfile and query database files for their versions.

    Returns a tuple:
        (xtandem_db_version, genome_db_version, taxref_db_version, annotation_db_version)
    """

    snakemake_config = yaml.load(open(snakemake_configfile))

    xtandem_db_version = get_xtandem_db_version(snakemake_config["xtandem_taxonomy"])
    genome_db_version =  get_genome_db_version(snakemake_config["blat_genome_db"][0])
    taxref_db_version = get_taxref_db_version(snakemake_config["taxref_db"])
    annotation_db_version = get_annotation_db_version(snakemake_config["annotation_db"])

    return (xtandem_db_version, genome_db_version, taxref_db_version, annotation_db_version)


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

def count_disc_peps(filename, ranks=("species", "no", "subspecies")):
    """
    Count the number of discriminative peptides at the specified ranks.

    NOTE: 'no rank' gets split into 'no'. 
    """
    ranks = set(ranks)
    with open(filename) as f:
        disc_peps = 0
        _ = [f.readline() for x in range(2)] # Skip the first two header lines
        for line in f:
            if line.split()[2] in ranks:
                disc_peps += 1
    return disc_peps


def get_summary_results(pid):
    """
    Compile summary results for Google Docs spreadsheet.

    Assumes workdir is the TTT proteotyping pipeline base dir,
    with output files in the following folders:
    ./3.fasta/
    ./5.results/<pid>/<pid>.taxonomic_composition.txt
                      <pid>.unique_bacterial_proteins.txt
                      <pid>.unique_human_proteins.txt
                      <pid>.discriminative_peptides.txt

    Returns a namedtuple with the following fields:
      pid
      unique_proteins
      human_proteins
      peptides,
      disc_peps
      completion_date
    """ 

    Results = namedtuple("Results", 
            ["pid", 
             "unique_proteins", 
             "human_proteins",
             "peptides",
             "disc_peps",
             "completion_date"])

    # Construct the paths to all the required files
    resultsdir_base = "5.results/"+pid+"/"+pid
    taxcomp_filename = resultsdir_base + ".taxonomic_composition.txt"
    unique_proteins_filename = resultsdir_base + ".unique_bacterial_proteins.txt"
    human_proteins_filename = resultsdir_base + ".unique_human_proteins.txt"
    disc_peps_filename = resultsdir_base + ".discriminative_peptides.txt"
    num_peps_filename = "3.fasta/" + pid + ".bacterial.fasta"

    # Use all the filenames to retrieve the relevanta data

    unique_proteins = get_count_proteins(unique_proteins_filename)
    logging.debug("Got %s bacterial proteins from %s", unique_proteins, unique_proteins_filename)

    human_proteins = get_count_proteins(human_proteins_filename)
    logging.debug("Got %s human proteins from %s", human_proteins, human_proteins_filename)

    num_peps = count_num_peps("3.fasta/"+pid+".bacterial.fasta")
    logging.debug("Counted %s peptides in %s", num_peps, num_peps_filename)

    disc_peps = count_disc_peps(resultsdir_base+".discriminative_peptides.txt")
    logging.debug("Got %s discriminative peptides from %s", disc_peps, disc_peps_filename)

    completion_date = datetime.fromtimestamp(getmtime(taxcomp_filename)).strftime("%Y-%m-%d")
    logging.debug("Got completion date %s for %s", completion_date, taxcomp_filename)


    results = Results(pid, 
            unique_proteins, 
            human_proteins, 
            num_peps, 
            disc_peps,
            completion_date
            )
    return results


class Samples_DB():
    """
    Simple wrapper over an SQLite3 in-memory database to store the sample DB from Gdoc.
    """

    def __init__(self):
        con = sqlite3.connect(":memory:")
        self.db = con
        create_table_samples = """CREATE TABLE samples(
            eu int,
            project text,
            pid text,
            pnotes text,
            species text,
            mixratio text,
            notes text)
        """
        self.db.execute(create_table_samples)

    def fill_samples_table(self, values):
        self.db.executemany("INSERT INTO samples VALUES (?,?,?,?,?,?,?)", values)
        self.db.commit()

    def get_samples(self):
        result = self.db.execute("SELECT * FROM samples")
        return result.fetchall()

    def __getitem__(self, key):
        """Overloaded to retrieve rows from the DB using QE-number as key."""
        result = self.db.execute("SELECT * FROM samples WHERE pid = ?", (key,)).fetchone()
        if result is None:
            raise KeyError(key)
        return result


def read_samples_db_from_gdoc(tokenfile, spreadsheet="TTT proteotyping pipeline results"):
    """
    Read the samples database from Google Docs spreadsheet.

    It expects to find it in the "Samples" sheet.
    """
    json_key = json.load(open(options.tokenfile))
    scope = ["https://spreadsheets.google.com/feeds"]

    logging.debug("Signing in to Google account %s\n  with credentials from %s", 
            json_key["client_email"], options.tokenfile)
    credentials = SignedJwtAssertionCredentials(json_key['client_email'], 
                                                json_key['private_key'].encode(), 
                                                scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(spreadsheet).worksheet("Samples")

    list_of_lists = wks.get_all_values()
    samples_db = Samples_DB()
    samples_db.fill_samples_table(list_of_lists)
    return samples_db


def report_to_gdoc_r3(results, sample_db, db_versions, tokenfile, spreadsheet="TTT proteotyping pipeline results"):
    """
    Upload TTT proteotyping pipeline results to Google Docs spreadsheet.
    
    Connects to Google docs using the 'gspread' Python package. 
    Authentication via OAuth2 credentials from Google Developers Console.
    """
    json_key = json.load(open(options.tokenfile))
    scope = ["https://spreadsheets.google.com/feeds"]

    logging.debug("Signing in to Google account %s\n  with credentials from %s", 
            json_key["client_email"], options.tokenfile)
    credentials = SignedJwtAssertionCredentials(json_key['client_email'], 
                                                json_key['private_key'].encode(), 
                                                scope)
    gc = gspread.authorize(credentials)
    wks = gc.open(spreadsheet).worksheet("TPARTY results")

    hostname = platform.node().split(".")[0]
    logging.debug("Got hostname %s", hostname)

    #results = [("EUNUM", "QENUM", "PROJECT", "SPECIES", "HOSTNAME", "XTANDEMDB", "GNEOMEDB", "TAXREFDB", "UNIQUE", "HUMANPROT", "PEPTIDES", "DISC", "COMPLETED")]
    for result in results:
        try:
            sample_info = sample_db[result.pid]
        except KeyError:
            logging.error("Found no info for %s in sample_db, is information about the sample entered in Gdoc??", result.pid)
            exit(1)
            continue
        eu = sample_info[0]
        project = sample_info[1]
        qe = sample_info[2]
        species = sample_info[4]
        row = [eu, project, qe, species, hostname]
        row.extend(db_versions)
        row.extend(result[1:])
        wks.append_row(row)


if __name__ == "__main__":
    options = parse_commandline(argv)

    results = [get_summary_results(pid) for pid in options.PID]

    samples_db = read_samples_db_from_gdoc(options.tokenfile)
    db_versions = get_database_versions(options.snakemake_configfile)
    report_to_gdoc_r3(results, samples_db, db_versions, options.tokenfile)
