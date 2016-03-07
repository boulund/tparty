# vi:syntax=python
# vi:filetype=python
# coding: utf-8
#
# Snakemake file for TTT proteotyping analysis workflow
# Fredrik Boulund 2016

# Load configuration from YAML config file.
# The config parameters are stored in global dict 'config'.
configfile: "/home/boulund/research/TTT/code/TTT_proteotyping_pipeline/TTT_pipeline_snakemake_config.yaml"

#####################################################################
# Define SAMPLES to run on
#####################################################################
# All *.raw files present in config["rawdir"] will be included in the 
# SAMPLES list of all samples to process.
SAMPLES = glob_wildcards(config["rawdir"]+"/{sample}.raw").sample


#####################################################################
# Pseudo target rules
#####################################################################

# All of these rules have quite low performance impact and can
# easily be run as local rules (i.e. if run in cluster environment,
# these rules will be run on the login node).
localrules: 
	all, 
	all_proteotyping, 
	all_resistance, 
	all_human,
	upto_mzxml, 
	upto_xtandem,
	upto_fasta,
	upto_unique_bacterial_proteins,
	raw2mzxml,
	bacterial_xml2fasta,
	unique_bacterial_proteins,
	unique_human_proteins,
	determine_resistance


rule all:
	input:
		expand(config["resultsdir"]+"/{sample}.taxonomic_composition.xlsx", sample=SAMPLES),
		expand(config["resultsdir"]+"/{sample}.taxonomic_composition.txt", sample=SAMPLES),
		expand(config["resultsdir"]+"/{sample}.unique_bacterial_proteins.txt", sample=SAMPLES),
		expand(config["resultsdir"]+"/{sample}.resistance.txt", sample=SAMPLES),
		expand(config["resultsdir"]+"/{sample}.unique_human_proteins.txt", sample=SAMPLES)


rule all_proteotyping:
	input:
		expand(config["resultsdir"]+"/{sample}.taxonomic_composition.txt", sample=SAMPLES),
		expand(config["resultsdir"]+"/{sample}.taxonomic_composition.xlsx", sample=SAMPLES),
		expand(config["resultsdir"]+"/{sample}.unique_bacterial_proteins.txt", sample=SAMPLES)

rule all_resistance:
	input:
		expand(config["resultsdir"]+"/{sample}.resistance.txt", sample=SAMPLES)

rule all_human:
	input:
		expand(config["resultsdir"]+"/{sample}.unique_human_proteins.txt", sample=SAMPLES)


rule upto_mzxml:
	input:
		expand(config["mzXMLdir"]+"/{sample}.mzXML.gz", sample=SAMPLES)

rule upto_xtandem:
	input:
		expand(config["xmldir"]+"/{sample}.bacterial.xml", sample=SAMPLES)

rule upto_fasta:
	input:
		expand(config["fastadir"]+"/{sample}.bacterial.fasta", sample=SAMPLES)

rule upto_blast8:
	input:
		expand(config["blast8dir"]+"/{sample}.bacterial.blast8", sample=SAMPLES),
		expand(config["blast8dir"]+"/{sample}.resistance.blast8", sample=SAMPLES),

rule upto_unique_bacterial_proteins:
	input:
		expand(config["resultsdir"]+"/{sample}.unique_bacterial_proteins.txt", sample=SAMPLES)


#####################################################################
# Actual Workflow target rules
#####################################################################

#######################################
## Shared steps
#######################################

rule raw2mzxml:
	"""raw to mzXML conversion using ReAdW in Wine"""
	input:
		config["rawdir"]+"/{sample}.raw"
	output:
		config["mzXMLdir"]+"/{sample}.mzXML.gz"
	shell:
		"""
		export READW={config[readw_exe]}
		export WINEPREFIX={config[wineprefix]}
		wine $READW --centroid --nocompress --gzip {input} {output}
		"""

rule xtandem_bacterial:
	"""Run X! Tandem on protein/peptide DB"""
	input:
		config["mzXMLdir"]+"/{sample}.mzXML.gz"
	output:
		temp("./{sample}.mzXML"),
		temp("./input_{sample}.xml"),
		xmlfile=config["xmldir"]+"/{sample}.bacterial.xml"
	log:
		"input_{sample}.xml.log"
	threads: 
		config["xtandem_threads"]
	shadow: 
		True
	# X!Tandem annoyingly appends the run date and time to
	# the filename. The file needs to be renamed after X!Tandem finishes.
	shell:
		"""
		echo 'run_xtandem.py --output {output.xmlfile} -n {threads} --db {config[xtandem_db]} --loglevel {config[loglevel]} {input}'
		echo 'mv {output.xmlfile}* {config[xmldir]}/{wildcards.sample}.xml'
		"""

rule bacterial_xml2fasta:
	"""Convert X! Tandem output XML to sequences in FASTA"""
	input:
		config["xmldir"]+"/{sample}.bacterial.xml"
	output:
		config["fastadir"]+"/{sample}.bacterial.fasta"
	shell:
		"""
		convert_xtandem_xml_2_fasta.py {input} {output}
		"""

#######################################
## Taxonomic composition determination
#######################################

rule unique_bacterial_proteins:
	"""Create list of unique proteins in X!Tandem output"""
	input:
		config["xmldir"]+"/{sample}.bacterial.xml"
	output:
		config["resultsdir"]+"/{sample}.unique_bacterial_proteins.txt"
	shell:
		"""
		create_unique_protein_list.py -o {output}
		"""

rule blat_bacterial:
	"""pBLAT translated search against reference sequence database"""
	input:
		config["fastadir"]+"/{sample}.bacterial.fasta"
	output:
		config["blast8dir"]+"/{sample}.bacterial.blast8"
	threads: 
		config["blat_threads"]
	shadow:
		True
	shell:
		"""
		pblat {config[blat_genome_db]} {input} -threads={threads} -out=blast8 -t=dnax -q=prot -tileSize=5 -stepSize=5 -minIdentity=90 {output}
		"""

rule taxonomic_composition:
	"""Perform proteotyping (determine taxonomic composition) of sample based 
	on sequences matched by pBLAT"""
	input:
		config["blast8dir"]+"/{sample}.bacterial.blast8"
	output:
		results=config["resultsdir"]+"/{sample}.taxonomic_composition.txt",
		xlsx=config["resultsdir"]+"/{sample}.taxonomic_composition.xlsx"
	log:
		"{sample}.results.log"
	shell:
		"""
		proteotyping.py {input} --output {output.results} --blacklist {config[blacklist]} --write-xlsx --loglevel {config[loglevel]}
		"""


#######################################
## Antibiotic resistance detection
#######################################

rule blat_resistance:
	"""pBLAT protein-to-protein search against resistance gene database"""
	input:
		config["fastadir"]+"/{sample}.bacterial.fasta"
	output:
		config["blast8dir"]+"/{sample}.resistance.blast8"
	threads:
		config["blat_threads"]
	shadow:
		True
	shell:
		"""
		pblat {config[blat_resistance_db]} {input} -threads={threads} -out=blast8 -prot -minIdentity=90 {output}
		"""

rule determine_resistance:
	"""Parse and filter resistance gene hits"""
	input:
		config["blast8dir"]+"/{sample}.resistance.blast8"
	output:
		config["resultsdir"]+"/{sample}.resistance.txt"
	shell:
		"""
		parse_AR_blast8.py --resfinder {config[resfinder_sqlite3_db]} --min-identity {config[resistance_min_identity]} --keep-going --output {output}
		"""


#######################################
## Human protein detection
#######################################

rule xtandem_human:
	"""Run X! Tandem on human proteome sequences"""
	input:
		config["mzXMLdir"]+"/{sample}.mzXML.gz"
	output:
		temp("./{sample}.mzXML"),
		temp(".input_{sample}.xml"),
		xmlfile=config["xmldir"]+"/{sample}.human.xml"
	log:
		"input_{sample}.xml.log"
	threads: 
		config["xtandem_threads"]
	shadow:
		True
	# X!Tandem annoyingly appends the run date and time to
	# the filename. The file needs to be renamed after X!Tandem finishes.
	shell:
		"""
		echo 'run_xtandem.py --output {output.xmlfile} -n {threads} --db {config[human_proteome]} --loglevel {config[loglevel]} {input}'
		echo 'mv {output.xmlfile}* {config[xmldir]}/{wildcards.sample}.human.xml'
		"""

rule unique_human_proteins:
	"""Create list of unique proteins in X!Tandem xml output"""
	input:
		config["xmldir"]+"/{sample}.human.xml"
	output:
		config["resultsdir"]+"/{sample}.unique_human_proteins.txt"
	shell:
		"""
		create_unique_protein_list.py -o {output}
		"""


