#!/usr/bin/env python3.5
# Count and list unique proteins in X!Tandem XML output.
# Fredrik Boulund 2016

from sys import argv, exit, stdout
from os import path, makedirs
import argparse
import logging
import sqlite3
from lxml import etree


def parse_commandline():
    """
    Parse commandline.
    """

    desc = """Extract unique protein information from X!Tandem XML output files. Fredrik Boulund 2016"""

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("FILE", type=str,
            help="Filename of output XML file(s) to summarize")
    parser.add_argument("-o", dest="outfile", metavar="OUTFILE", type=str,
            help="Output filename, default is <input_filename>_unique_proteins.txt.")
    parser.add_argument("--loglevel", 
            choices=["INFO", "DEBUG"],
            default="INFO",
            help="Set logging level [%(default)s].")

    if len(argv)<2:
        parser.print_help()
        exit()

    options = parser.parse_args()

    logging.basicConfig(level=options.loglevel)
    return options


def extract_seqences_from_bioml_xml(xmlfile):
    """
    Extracts sequence entries from X!Tandem BIOML XML file.

    This is a generator, meant to be used as an iterator.
    """

    for _, element in etree.iterparse(xmlfile):
        if element.tag == "group":
            if element.attrib["type"] == "model":
                group = element.attrib
            for domain in element.iterdescendants("domain"):
                yield group, domain.attrib
            # Free up memory when done with this node.
            # Without this call, memory usage increases monotonically,
            # making parsing a common ~500 MB BIOML XML file consume
            # more than 5 GiB of RAM! With this call, memory usage
            # should stay below 200 MiB in most cases.
            element.clear()  


def get_unique_proteins(xmlfile):
    """
    Returns unique proteins encountered in X!Tandem BIOML XML file.

    Unique proteins are determined by their FASTA headers.
    Several different peptides can come from the same protein header.
    """

    headers = (group["label"] for group, domain in extract_seqences_from_bioml_xml(xmlfile))
    return set(headers)


def main(options):
    """
    Main.
    """
    
    unique_headers = get_unique_proteins(options.FILE) 

    if options.outfile:
        outfilename = options.outfile
    else:
        outfilename = path.split(options.FILE)[1]+"_unique_proteins.txt"
    with open(outfilename, 'w') as outfile:
        logging.info("Writing unique proteins to '{}'.".format(outfilename))
        print("Found {} unique proteins for {}".format(len(unique_headers), options.FILE),
                file=outfile)
        for header in sorted(list(unique_headers), reverse=True):
            print(header, file=outfile)


if __name__ == "__main__":
    options = parse_commandline()
    main(options)

