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
import argparse
import logging
from os import path, makedirs
from lxml import etree


def parse_commandline():
    """
    Parse commandline.
    """

    desc = """Convert X!Tandem XML output files to FASTA. Fredrik Boulund 2016"""

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("FILE", type=str, nargs="+",
        help="Filename of output XML file to convert to FASTA")
    parser.add_argument("-d", "--outdir", dest="outdir", metavar="DIR", 
        type=str,
        default="fasta",
        help="Output directory [%(default)s].")
    parser.add_argument("-o", "--outfile", dest="outfile", metavar="FILE", 
        default="",
        help="Output filename. If specified only one file is expected and outdir is disregarded.")
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



def generate_seqences_from_bioml_xml(xmlfile):
    """
    Generates sequence entries from X!tandem BIOML XML file.

    Only returns the first peptide for each spectrum. 
    """

    for _, element in etree.iterparse(xmlfile):
        if element.tag == "group":
            for child in element.iterdescendants("domain"):
                yield (element.attrib["label"], 
                       child.attrib["id"], 
                       child.attrib["expect"], 
                       child.attrib["hyperscore"], 
                       element.attrib["z"],
                       element.attrib["mh"],
                       child.attrib["seq"])
                break
            element.clear()
            continue


def convert_tandem_bioml_to_fasta(xmlfile, outdir, outfile, min_hyperscore, max_evalue):
    """
    Converts X!tandem output BIOML XML to FASTA, writes to file in outdir.
    """

    if outfile:
        outfilename = outfile
    else:
        outfilename = path.join(outdir, path.splitext(path.basename(xmlfile))[0]+".fasta")
        if not path.exists(outdir):
            makedirs(outdir)

    logging.debug("Writing FASTA to '%s'", outfilename)
    sourceheaders = set()
    write_counter = 0
    with open(outfilename, 'w') as fastafile:
        for sourceheader, identity, expect, hyperscore, charge, mass, sequence in generate_seqences_from_bioml_xml(xmlfile):
            if float(expect) <= max_evalue and float(hyperscore) >= min_hyperscore:
                sourceheaders.add(sourceheader)
                logging.debug("Writing seq %s with length %s, expect %s, hyperscore %s, charge %s, mass %s.", identity, sequence, expect, hyperscore, charge, mass)
                header = ">{}_{} expect={} hyperscore={} z={} mh={}".format(identity, len(sequence), expect, hyperscore, charge, mass)
                fastafile.write("{}\n{}\n".format(header, sequence))
                write_counter += 1
    logging.info("Wrote %s peptide fragments from %s unique protein sequences to %s", write_counter, len(sourceheaders), outfilename)


def main(options):
    """
    Main.
    """
    for xmlfile in options.FILE:
        convert_tandem_bioml_to_fasta(xmlfile, options.outdir, options.outfile,
                options.min_hyperscore, options.max_evalue)


if __name__ == "__main__":
    options = parse_commandline()
    if options.outfile and len(options.FILE) > 1:
        logging.error("Cannot specify output filename with more than one file on command line")
        exit()
    main(options)
