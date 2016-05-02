# vi:syntax=python filetype=python tabstop=4 expandtab
# coding: utf-8
#
# Snakemake file for TTT proteotyping analysis workflow
# NOTE: THIS SNAKEFILE REQUIRES A CONFIGFILE TO SUPPLY 
#       CONFIGURATION PARAMETERS FOR ALL CALLED PROGRAMS
#       RUN THIS SNAKEFILE WITH THE --configfile PARAMETER
# Fredrik Boulund 2016

# Shadow rules are essential for not cluttering the root directory, especially
# for the X!Tandem and BLAT rules. They were introduced to Snakemake in 3.5.
from snakemake.utils import min_version
min_version("3.5")  

# Set workdir
workdir: config["workdir"]

onsuccess:
    print("Workflow finished without errors.")

# Send an email notifying that there was an error.
onerror:
    print("Workflow finished with error(s).")
    print("Check the logfile and fix errors until next workflow invocation.")
    shell("""mail -s "TTT Proteotyping Pipeline: error(s) occured." {config[email]} < {log}""")


#####################################################################
# Define SAMPLES to run on
#####################################################################
# All *.raw files present in config["rawdir"] will be included in the 
# SAMPLES list of all samples to process.
SAMPLES = glob_wildcards(config["rawdir"]+"/{sample}.raw").sample
DBTAXA = ["bacterial", "human"]
DBTYPES = ["bacterial", "resistance"]


#####################################################################
# Pseudo target rules
#####################################################################

# All of these rules have quite low performance impact and can
# easily be run as local rules (i.e. if run in cluster environment,
# these rules will be run on the login node).
localrules: 
    all, 
    compress_completed_intermediaries,
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
    determine_resistance,
    gzip


rule all:
    input:
        expand(config["resultsdir"]+"/{sample}/{sample}.taxonomic_composition.{filetype}", sample=SAMPLES, filetype=["xlsx", "txt"]),
        expand(config["resultsdir"]+"/{sample}/{sample}.unique_{dbtaxa}_proteins.txt", sample=SAMPLES, dbtaxa=DBTAXA),
        expand(config["resultsdir"]+"/{sample}/{sample}.resistance.txt", sample=SAMPLES),
        expand(config["resultsdir"]+"/{sample}/{sample}.gspread_reported", sample=SAMPLES),

rule compress_completed_intermediaries:
    """Compress intermediary files. WARNING: Will essentially run all rules to
    produce the compressed intermediaries."""
    input:
        expand(config["resultsdir"]+"/{sample}/{sample}.sqlite3.gz", sample=SAMPLES),
        expand(config["blast8dir"]+"/{sample}.{dbtype}.blast8.gz", sample=SAMPLES, dbtype=DBTYPES),
        expand(config["fastadir"]+"/{sample}.bacterial.fasta.gz", sample=SAMPLES),
        expand(config["xmldir"]+"/{sample}.{dbtaxa}.xml.gz", sample=SAMPLES, dbtaxa=DBTAXA)

rule all_proteotyping:
    input:
        expand(config["resultsdir"]+"/{sample}/{sample}.taxonomic_composition.{filetype}", sample=SAMPLES, filetype=["xlsx", "txt"]),
        expand(config["resultsdir"]+"/{sample}/{sample}.unique_bacterial_proteins.txt", sample=SAMPLES)

rule all_resistance:
    input:
        expand(config["resultsdir"]+"/{sample}/{sample}.resistance.txt", sample=SAMPLES)

rule all_human:
    input:
        expand(config["resultsdir"]+"/{sample}/{sample}.unique_human_proteins.txt", sample=SAMPLES)


rule upto_mzxml:
    input:
        expand(config["mzXMLdir"]+"/{sample}.mzXML.gz", sample=SAMPLES)

rule upto_xtandem:
    input:
        expand(config["xmldir"]+"/{sample}.bacterial.xml", sample=SAMPLES),
        expand(config["xmldir"]+"/{sample}.human.xml", sample=SAMPLES)

rule upto_fasta:
    input:
        expand(config["fastadir"]+"/{sample}.bacterial.fasta", sample=SAMPLES),
        expand(config["fastadir"]+"/{sample}.human.fasta", sample=SAMPLES)

rule upto_blast8:
    input:
        expand(config["blast8dir"]+"/{sample}.bacterial.blast8", sample=SAMPLES),
        expand(config["blast8dir"]+"/{sample}.resistance.blast8", sample=SAMPLES),

rule upto_unique_bacterial_proteins:
    input:
        expand(config["resultsdir"]+"/{sample}/{sample}.unique_bacterial_proteins.txt", sample=SAMPLES)


#####################################################################
# Actual Workflow target rules
#####################################################################

#######################################
## Shared rules
#######################################

rule raw2mzxml:
    """raw to mzXML conversion using ReAdW in Wine"""
    input:
        config["rawdir"]+"/{sample}.raw"
    output:
        config["mzXMLdir"]+"/{sample}.mzXML.gz"
    resources:
        io=1
    shell:
        """
        export READW={config[readw_exe]}
        export WINEPREFIX={config[wineprefix]}
        wine $READW --nocompress --gzip {input} {output}
        """

rule xtandem_bacterial:
    """Run X! Tandem on protein/peptide DB"""
    input:
        config["mzXMLdir"]+"/{sample}.mzXML.gz"
    output:
        xmlfile=config["xmldir"]+"/{sample}.bacterial.xml"
    log:
        "input_{sample}.xml.log"
    resources:
        mem=40
    threads: 
        config["xtandem_threads"]
    shadow:
        True
    shell:
        """
        run_parallel_tandem.py \
                --output {output.xmlfile} \
                -x {config[xtandem_exe]} \
                -n {threads} \
                --db {config[xtandem_db]} \
                --loglevel {config[loglevel]} \
                {input}
        """

rule bacterial_xml2fasta:
    """Convert X! Tandem output XML to sequences in FASTA"""
    input:
        config["xmldir"]+"/{sample}.bacterial.xml"
    output:
        config["fastadir"]+"/{sample}.bacterial.fasta"
    shell:
        """
        convert_tandem_xml_2_fasta.py {input} --outfile {output}
        """

#######################################
## Taxonomic composition estimation
#######################################

rule unique_bacterial_proteins:
    """Create list of unique proteins in X!Tandem output"""
    input:
        config["xmldir"]+"/{sample}.bacterial.xml"
    output:
        config["resultsdir"]+"/{sample}/{sample}.unique_bacterial_proteins.txt"
    shell:
        """
        create_unique_protein_list.py -o {output} {input}
        """

rule blat_bacterial:
    """BLAT translated search against reference sequence database"""
    input:
        config["fastadir"]+"/{sample}.bacterial.fasta"
    output:
        config["blast8dir"]+"/{sample}.bacterial.blast8"
    resources:
        mem=25
    shadow:
        True
    shell:
        """
        blat \
            {config[blat_genome_db]} \
            {input} \
            -out=blast8 \
            -t=dnax \
            -q=prot \
            -tileSize=5 \
            -stepSize=5 \
            -minIdentity=90 \
            {output}
        """

rule taxonomic_composition:
    """Perform proteotyping (determine taxonomic composition) of sample based 
    on sequences matched by pBLAT"""
    input:
        config["blast8dir"]+"/{sample}.bacterial.blast8"
    output:
        sample_db=config["resultsdir"]+"/{sample}/{sample}.sqlite3",
        results=config["resultsdir"]+"/{sample}/{sample}.taxonomic_composition.txt",
        xlsx=config["resultsdir"]+"/{sample}/{sample}.taxonomic_composition.xlsx",
        discpeps=config["resultsdir"]+"/{sample}/{sample}.discriminative_peptides.txt"
    log:
        config["resultsdir"]+"/{sample}/{sample}.proteotyping.log"
    shell:
        """
        taxonomic_composition {input} \
                --taxref-db {config[taxref_db]} \
                --annotation-db {config[annotation_db]} \
                --blacklist {config[blacklist]} \
                --write-xlsx {output.xlsx} \
                --write-discriminative-peptides {output.discpeps} \
                --loglevel {config[loglevel]} \
                --logfile {log} \
                --sample-db {output.sample_db} \
                --output {output.results}
        """


#######################################
## Antibiotic resistance detection
#######################################

rule blat_resistance:
    """BLAT protein-to-protein search against resistance gene database"""
    input:
        config["fastadir"]+"/{sample}.bacterial.fasta"
    output:
        config["blast8dir"]+"/{sample}.resistance.blast8"
    shadow:
        True
    shell:
        """
        blat \
            {config[blat_resistance_db]} \
            {input} \
            -out=blast8 \
            -prot \
            -minIdentity=90 \
            {output}
        """

rule determine_resistance:
    """Parse and filter resistance gene hits"""
    input:
        config["blast8dir"]+"/{sample}.resistance.blast8"
    output:
        config["resultsdir"]+"/{sample}/{sample}.resistance.txt"
    shell:
        """
        antibiotic_resistance \
            --resfinder {config[resfinder_sqlite3_db]} \
            --min-identity {config[resistance_min_identity]} \
            --keep-going \
            --output {output} \
            {input}
        """


#######################################
## Human protein detection
#######################################

rule xtandem_human:
    """Run X! Tandem on human proteome sequences"""
    input:
        config["mzXMLdir"]+"/{sample}.mzXML.gz"
    output:
        xmlfile=config["xmldir"]+"/{sample}.human.xml"
    log:
        "input_{sample}.xml.log"
    threads: 
        config["xtandem_threads"]
    shadow:
        True
    shell:
        """
        run_xtandem.py \
            --output {output.xmlfile} \
            -x {config[xtandem_exe]} \
            -n {threads} \
            --db {config[human_proteome]} \
            --loglevel {config[loglevel]} \
            {input}
        """

rule unique_human_proteins:
    """Create list of unique proteins in X!Tandem xml output"""
    input:
        config["xmldir"]+"/{sample}.human.xml"
    output:
        config["resultsdir"]+"/{sample}/{sample}.unique_human_proteins.txt"
    shell:
        """
        create_unique_protein_list.py -o {output} {input}
        """


#######################################
## Google Docs Spreadsheet reporting
#######################################
rule gspread_report:
    """Report results to Google Docs spreadsheet"""
    input:
        taxcomp=config["resultsdir"]+"/{sample}/{sample}.taxonomic_composition.txt",
        bac_prot=config["resultsdir"]+"/{sample}/{sample}.unique_bacterial_proteins.txt",
        hum_prot=config["resultsdir"]+"/{sample}/{sample}.unique_human_proteins.txt",
        disc_peps=config["resultsdir"]+"/{sample}/{sample}.discriminative_peptides.txt",
        peps=config["fastadir"]+"/{sample}.bacterial.fasta"
    output:
        config["resultsdir"]+"/{sample}/{sample}.gspread_reported"
    log:
        config["resultsdir"]+"/{sample}/{sample}.gspread_report.log"
    shell:
        """
        gspread_report.py \
                --tokenfile {config[google_token]} \
                --logfile {log} \
                {wildcards.sample}
        touch {output}
        """


#######################################
## Misc. other rules
#######################################
rule gzip:
    """Compress files with gzip"""
    input:
        "{filename}"
    output:
        "{filename}.gz"
    resources:
        io=1
    priority:
        0
    shell:
        """
        gzip {input}
        """
