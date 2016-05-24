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


INPUT_XML = """<?xml version="1.0"?>
<bioml>
	<note type="input" label="list path, default parameters">{defaults}</note>
	<note type="input" label="list path, taxonomy information">{taxonomy}</note>
	<note type="input" label="protein, taxon">{taxon}</note>
	<note type="input" label="spectrum, threads">{threads}</note>
	<note type="input" label="spectrum, path">{input}</note>
	<note type="input" label="output, path">{output}</note>
</bioml>"""


def parse_commandline():
    """
    Parses commandline.
    """

    desc="""Convenience wrapper for running X! Tandem. Fredrik Boulund 2016."""

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("FILES", metavar="MZXML", nargs="+",
            help="""Input mzXML file to search against database with (can be gzipped).""")
    parser.add_argument("-o", "--output", metavar="FILE", 
            help="Output filename.")
    parser.add_argument("-d", "--taxon", "--db", metavar="TAXON", dest="taxon",
            default="bacteria",
            help="Taxon database to search (must be specified in taxonomy.xml) [%(default)s].")
    parser.add_argument("-t", "--taxonomy", metavar="FILE", dest="taxonomy",
            required=True,
            help="Path to X!Tandem taxonomy.xml [%(default)s].")
    parser.add_argument("-p", "--default-parameters", metavar="FILE", dest="default_parameters",
            required=True,
            help="Path to X!Tandem default_parameters.xml [%(default)s].")
    parser.add_argument("-n", "--threads", dest="threads",
            default=10,
            help="Number of threads to use [%(default)s].")
    parser.add_argument("-x", "--xtandem", dest="xtandem_path",
            default="/storage/TTT/bin/tandem.exe",
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


def run_xtandem(input_xml_filename, output_xml_filename, xtandem_executable):
    """
    Runs X!tandem on a single mzXML file defined in an input_{samplename}.xml.
    """
    xtandem_call = shlex.split("{xtandem_path} {inputxml}".format(xtandem_path=xtandem_executable, inputxml=input_xml_filename))
    logging.debug("X!tandem call: %s", " ".join(xtandem_call))
    logging.info("Running X!tandem on %s", input_xml_filename)
    xtandem = Popen(xtandem_call, stdout=PIPE, stderr=PIPE)
    xtandem_output = xtandem.communicate()

    if xtandem.returncode != 0:
        logging.error("X!Tandem error: %s\n%s", xtandem_output[0].decode("utf-8"), 
                xtandem_output[1].decode("utf-8"))
        try:
            with open(output_xml_filename, "rb") as outputxml:
                outputxml.seek(-9, SEEK_END)
                last_line = outputxml.readline()
            if last_line == "</bioml>\n":
                logging.warning("X!tandem returned non-zero exit code, but outputfile looks OK!")
            else:
                logging.error("X!tandem returned non-zero exit code, and outputfile appears incomplete!")
        except FileNotFoundError as e:
            logging.error("Unrecoverable X!Tandem error: %s", e)
            exit(1)
    else:
        logging.info("Finished running X!Tandem on %s.", input_xml_filename)

    with open(input_xml_filename+".log", "w") as log:
        logging.debug("Writing X!tandem stdout (and stderr) to file %s", log.name)
        log.write(xtandem_output[0].decode("utf8"))
        log.write("\nSTDERR:\n")
        log.write(xtandem_output[1].decode("utf8"))


def generate_xtandem_input_files(inputfiles, taxon, default_parameters, taxonomy, threads, output_filename):
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
            if not output_filename:
                output_filename = "output_"+samplename+".xml"
            input_xml.write(INPUT_XML.format(defaults=default_parameters, 
                taxonomy=taxonomy,
                taxon=taxon,  
                threads=threads,
                input=samplename, 
                output=output_filename))
        logging.debug("Wrote file %s for sample %s", input_xml_filename, samplename)
        yield input_xml_filename, output_filename


def main():
    """
    Main function.
    """
    options = parse_commandline()

    for inputxml, outputxml in generate_xtandem_input_files(options.FILES, 
            options.taxon, 
            options.default_parameters, 
            options.taxonomy, 
            options.threads, 
            options.output):
        run_xtandem(inputxml, outputxml, options.xtandem_path)

if __name__ == "__main__":
    main()
