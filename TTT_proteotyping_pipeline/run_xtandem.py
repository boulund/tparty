#!/usr/bin/env python3.5
# Fredrik Boulund 2016
# Convenience script to generate X!Tandem input xml files and run X!Tandem.

from sys import argv, exit
from subprocess import Popen, PIPE
from glob import glob
from os import path, getcwd, chdir, mkdir, SEEK_END, listdir
from tempfile import mkdtemp
import shutil
import shlex
import subprocess
import argparse
import logging


def parse_commandline():
    """
    Parses commandline.
    """

    desc="""Convenience wrapper for running X! Tandem. Fredrik Boulund 2016."""

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("FILES", metavar="MZXML", nargs="+",
            help="""Input mzXML file to search against database with (can be gzipped).""")
    parser.add_argument("--output", metavar="FILE", 
            help="Output filename.")
    parser.add_argument("--db", metavar="DB",
            default="/storage/boulund/TTT/ms_refdb/ms_refdb.fasta",
            help="Database to search against [%(default)s].")
    parser.add_argument("-n", "--threads", dest="threads",
            default=10,
            help="Number of threads to use [%(default)s].")
    parser.add_argument("-x", "--xtandem", dest="xtandem_path",
            default="/home/boulund/research/TTT/src/xtandem-20151215/tandem-linux-15-12-15-2/bin/rhel_static_link/tandem.exe",
            help="Path to X!Tandem executable [%(default)s].")
    parser.add_argument("--loglevel", 
            choices=["INFO","DEBUG"],
            default="DEBUG",
            help="Set logging level [%(default)s]")
    
    if len(argv)<2:
        parser.print_help()
        exit()

    options = parser.parse_args()
    logging.basicConfig(level=options.loglevel, format='%(asctime)s %(levelname)s: %(message)s')
    return options


def run_xtandem(input_xml_filename, output_xml_filename, options):
    """
    Runs X!tandem on a single mzXML file defined in an input_{samplename}.xml.
    """
    xtandem_call = shlex.split("{xtandem_path} {inputxml}".format(xtandem_path=options.xtandem_path, inputxml=input_xml_filename))
    logging.debug("X!tandem call: %s", " ".join(xtandem_call))
    logging.info("Running X!tandem on %s", input_xml_filename)
    xtandem = Popen(xtandem_call, stdout=PIPE, stderr=PIPE)
    xtandem_output = xtandem.communicate()
    try: 
        logging.debug("Expecting X!Tandem output somewhere here: %s", output_xml_filename)
        xtandem_output_filename = glob(path.splitext(output_xml_filename)[0]+".*.xml")[-1]
        logging.debug("Found X!Tandem output file %s", xtandem_output_filename)
    except IndexError:
        logging.error("No X!Tandem output file detected")
        logging.error("stdout: %s", xtandem_output[0].decode("utf-8"))
        logging.error("stderr: %s", xtandem_output[1].decode("utf-8"))
        logging.error("current dir: %s", listdir('.'))
        exit()

    if xtandem.returncode != 0:
        with open(xtandem_output_filename, "rb") as outputxml:
            outputxml.seek(-9, SEEK_END)
            last_line = outputxml.readline()
        if last_line == "</bioml>\n":
            logging.warning("X!tandem returned non-zero exit code, but outputfile looks OK!")
        else:
            logging.error("X!tandem returned non-zero exit code, and outputfile appears incomplete!")
    else:
        logging.info("Finished running X!Tandem on %s.", input_xml_filename)

    with open(input_xml_filename+".log", "w") as log:
        logging.debug("Writing X!tandem stdout (and stderr) to file %s", log.name)
        log.write(xtandem_output[0].decode("utf8"))
        log.write("\nSTDERR:\n")
        log.write(xtandem_output[1].decode("utf8"))

    # Move annoyingly named X!Tandem output file to requested output location.
    logging.debug("Moving X!Tandem outputfile '%s' to '%s", xtandem_output_filename, output_xml_filename)
    shutil.move(xtandem_output_filename, output_xml_filename)


def create_misc_xtandem_files(options):
    """
    Creates a new workdir and generates the required X!tandem input files:
        - default_input.xml
        - input_{samplename}.xml
        - taxonomy.xml
    """

    with open("default_input.xml", "w") as default_input:
        default_input.write(PARAMETERS)
    logging.debug("Wrote default_input.xml")
    with open("taxonomy.xml", "w") as taxonomy:
        taxonomy.write(TAXONOMY.format(refdb=options.db))
    logging.debug("Wrote taxonomy.xml with refdb='%s'", options.db)


def generate_xtandem_input_files(inputfiles):
    """
    Creates input_FILENAME.xml for each input file.
    """

    for filename in inputfiles:
        filename_abspath = path.abspath(filename)
        samplename = path.splitext(path.basename(filename))[0]

        if filename.endswith((".gz", ".GZ")):
            logging.debug("Filename %s ends with .gz or .GZ", filename)
            gunzip_call = ["gunzip", "-c", filename_abspath]
            logging.debug("Gunzipping %s into %s", filename, samplename)
            with open(samplename, "w") as gunzipped:
                logging.debug("gunzip call: %s", gunzip_call)
                subprocess.call(gunzip_call, stdout=gunzipped)
            logging.debug("Unpacked the file to %s", samplename)

        logging.debug("Creating input XML for '%s'", filename)
        input_xml_filename = "input_"+samplename+".xml"
        with open(input_xml_filename, "w") as input_xml:
            if options.output:
                output = options.output
            else:
                output = "output_"+samplename+".xml"
            input_xml.write(INPUT_XML.format(input=samplename, output=output))
        logging.debug("Wrote file %s for sample %s", input_xml_filename, samplename)
        yield input_xml_filename, output


# COMPLETE INPUT FILES FOR X!!TANDEM AS STRINGS
PARAMETERS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<bioml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<note type="input" label="list path, default parameters">default_input.xml</note>
	<note type="input" label="list path, taxonomy information">taxonomy.xml</note>
	<note type="input" label="spectrum, fragment monoisotopic mass error">20</note>
	<note type="input" label="spectrum, parent monoisotopic mass error plus">5</note>
	<note type="input" label="spectrum, parent monoisotopic mass error minus">5</note>
	<note type="input" label="spectrum, parent monoisotopic mass isotope error">yes</note>
	<note type="input" label="spectrum, fragment monoisotopic mass error units">ppm</note>
	<note type="input" label="spectrum, parent monoisotopic mass error units">ppm</note>
	<note type="input" label="spectrum, fragment mass type">monoisotopic</note>
	<note type="input" label="spectrum, dynamic range">100.0</note>
	<note type="input" label="spectrum, total peaks">50</note>
	<note type="input" label="spectrum, maximum parent charge">4</note>
	<note type="input" label="spectrum, use noise suppression">yes</note>
	<note type="input" label="spectrum, minimum parent m+h">500.0</note>
	<note type="input" label="spectrum, minimum fragment mz">150.0</note>
	<note type="input" label="spectrum, minimum peaks">15</note>
	<note type="input" label="spectrum, threads">{threads}</note>
	<note type="input" label="spectrum, sequence batch size">1000</note>
	<note type="input" label="residue, modification mass">57.022@C</note>
	<note type="input" label="residue, potential modification mass" xsi:nil="true"/>
	<note type="input" label="residue, potential modification motif" xsi:nil="true"/>
	<note type="input" label="protein, taxon">other mammals</note>
	<note type="input" label="protein, cleavage site">[RK]|{{P}}</note>
	<note type="input" label="protein, modified residue mass file" xsi:nil="true"/>
	<note type="input" label="protein, cleavage C-terminal mass change">+17.002735</note>
	<note type="input" label="protein, cleavage N-terminal mass change">+1.007825</note>
	<note type="input" label="protein, N-terminal residue modification mass">0.0</note>
	<note type="input" label="protein, C-terminal residue modification mass">0.0</note>
	<note type="input" label="protein, homolog management">no</note>
	<note type="input" label="refine">yes</note>
	<note type="input" label="refine, modification mass" xsi:nil="true"/>
	<note type="input" label="refine, sequence path" xsi:nil="true"/>
	<note type="input" label="refine, tic percent">20</note>
	<note type="input" label="refine, spectrum synthesis">yes</note>
	<note type="input" label="refine, maximum valid expectation value">0.1</note>
	<note type="input" label="refine, potential N-terminus modifications">+42.010565@[</note>
	<note type="input" label="refine, potential C-terminus modifications" xsi:nil="true"/>
	<note type="input" label="refine, unanticipated cleavage">yes</note>
	<note type="input" label="refine, potential modification mass" xsi:nil="true"/>
	<note type="input" label="refine, point mutations">no</note>
	<note type="input" label="refine, use potential modifications for full refinement">no</note>
	<note type="input" label="refine, point mutations">no</note>
	<note type="input" label="refine, potential modification motif" xsi:nil="true"/>
	<note type="input" label="scoring, minimum ion count">4</note>
	<note type="input" label="scoring, maximum missed cleavage sites">1</note>
	<note type="input" label="scoring, x ions">no</note>
	<note type="input" label="scoring, y ions">yes</note>
	<note type="input" label="scoring, z ions">no</note>
	<note type="input" label="scoring, a ions">no</note>
	<note type="input" label="scoring, b ions">yes</note>
	<note type="input" label="scoring, c ions">no</note>
	<note type="input" label="scoring, cyclic permutation">no</note>
	<note type="input" label="scoring, include reverse">no</note>
	<note type="input" label="scoring, cyclic permutation">no</note>
	<note type="input" label="scoring, include reverse">no</note>
	<note type="input" label="output, log path" xsi:nil="true"/>
	<note type="input" label="output, message">.</note>
	<note type="input" label="output, one sequence copy">no</note>
	<note type="input" label="output, sequence path" xsi:nil="true"/>
	<note type="input" label="output, path">output.xml</note>
	<note type="input" label="output, sort results by">protein</note>
	<note type="input" label="output, path hashing">yes</note>
	<note type="input" label="output, xsl path">tandem-style.xsl</note>
	<note type="input" label="output, parameters">yes</note>
	<note type="input" label="output, performance">yes</note>
	<note type="input" label="output, spectra">yes</note>
	<note type="input" label="output, histograms">yes</note>
	<note type="input" label="output, proteins">yes</note>
	<note type="input" label="output, sequences">yes</note>
	<note type="input" label="output, one sequence copy">no</note>
	<note type="input" label="output, results">valid</note>
	<note type="input" label="output, maximum valid expectation value">0.1</note>
	<note type="input" label="output, histogram column width">30</note>
</bioml>"""


TAXONOMY = """<?xml version="1.0"?>
<bioml label="x! taxon-to-file matching list">
	<taxon label="bacteria">
		<file format="peptide" URL="{refdb}"/>
	</taxon>
</bioml>"""


INPUT_XML = """<?xml version="1.0"?>
<bioml>
	<note type="input" label="list path, default parameters">default_input.xml</note>
	<note type="input" label="list path, taxonomy information">taxonomy.xml</note>
	<note type="input" label="protein, taxon">bacteria</note>
	<note type="input" label="spectrum, path">{input}</note>
	<note type="input" label="output, path">{output}</note>
</bioml>"""


if __name__ == "__main__":
    options = parse_commandline()
    PARAMETERS = PARAMETERS.format(threads=options.threads)

    for inputxml, outputxml in generate_xtandem_input_files(options.FILES):
        create_misc_xtandem_files(options)
        xtandem_output_filename = run_xtandem(inputxml, outputxml, options)
