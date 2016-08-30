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
    parser.add_argument("-H", "--min-hyperscore", dest="min_hyperscore", metavar="H",
        type=float,
        default=0.0,
        help="Minimum hyperscore value [%(default)s].")
    parser.add_argument("-e", "--max-evalue", dest="max_evalue", metavar="e", 
        type=float,
        default=1e15,
        help="Maximum e-value [%(default)s].")
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

    Extracts only the first sequence for each domain in the file. 
    This is a generator, meant to be used as an iterator.
    """

    for _, element in etree.iterparse(xmlfile):
        if element.tag == "group":
            for child in element.iterdescendants("domain"):
                yield (element.attrib["label"], 
                       child.attrib["id"], 
                       float(child.attrib["expect"]),
                       float(child.attrib["hyperscore"]), 
                       element.attrib["z"],
                       element.attrib["mh"],
                       child.attrib["seq"])
                break
            # Free up memory when done with this node.
            # Without this call, memory usage increases monotonically,
            # making parsing a common ~500 MB BIOML XML file consume
            # more than 5 GiB of RAM! With this call, memory usage
            # should stay below 200 MiB in most cases.
            element.clear()  


def get_unique_proteins(xmlfile, max_evalue, min_hyperscore):
    """
    Returns unique proteins encountered in X!Tandem BIOML XML file.

    Unique proteins are determined by their FASTA headers.
    Several different peptides can come from the same protein header.
    """

    headers = (label 
               for label, pep_id, expect, hyperscore, z, mh, seq 
               in extract_seqences_from_bioml_xml(xmlfile) 
               if expect < max_evalue and hyperscore > min_hyperscore)
    return set(headers)


def main(options):
    """
    Main.
    """
    
    unique_headers = get_unique_proteins(options.FILE, options.max_evalue, options.min_hyperscore) 

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

