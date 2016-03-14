#!/bin/bash
# Snakemake crontab script
# Fredrik Boulund 2016

# The number of cores to run processes on. Some rules in the snakefile consume
# several threads. The maximum number of concurrent processes are limited by
# the number of cores set here, and for a rule requiring 11 CPUs only two
# simultaneous instances of that rule can run with 25 CPUs specified here.
CORES=25
# Set the process niceness (default processes run on 10; higher is lower
# priority).
NICENESS=12

# Lockfile used to indicate if snakemake workflow is currently running.
# 'flock' opens the file for reading to indicate when the workflow is running.
export LOCKFILE=/storage/TTT/.TTT_snakemake.lock

# Load environment variables required to activate conda environment
# Activate conda environment
# Change workdir to analysis dir
# Add TTT_pipeline executables to path
source $HOME/.bash_profile          
source activate proteotyping        
cd /storage/TTT/                    
export PATH=/storage/TTT/bin:$PATH  

# Run snakemake only if it isn't already currently running.
# flock creates a lockfile that, when open, indicates if the workflow in
# currently in progress. flock detects if the file is already opened and 
# the -n command makes it do nothing if snakemake is already running.
flock -n $LOCKFILE \
	nice $NICENESS \
	snakemake \
		--snakefile TTT_pipeline.snakefile \
		--configfile TTT_pipeline_snakemake_config.yaml \
		--cores $CORES \
		--keep-going
		$1
