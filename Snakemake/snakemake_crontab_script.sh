#!/bin/bash
# Snakemake crontab script
# Fredrik Boulund 2016

# The number of cores to run processes on. Some rules in the snakefile consume
# several threads. The maximum number of concurrent processes are limited by
# the number of cores set here, and for a rule requiring 11 CPUs only two
# simultaneous instances of that rule can run with 25 CPUs specified here.
CORES=25
# Other limiting resources; mem, io
# e.g. MEM=256 on a machine with 256 GB memory available for the pipeline
# will limit the number of concurrent BLAT processes to about 10, since
# each process requires 25 of the "mem" resource.
# Setting IO=10 limits the number of concurrent IO-heavy jobs to 10,
# at the time of this writing this is only the raw2mzxml rule
MEM=160
IO=10
# Adjust the process niceness (default processes run on 10; higher is lower
# priority). 
NICENESS=12

# Lockfile used to indicate if snakemake workflow is currently running.
# 'flock' opens the file for reading to indicate when the workflow is running.
export LOCKFILE=/storage/TTT/.TTT_snakemake.lock

# Load environment variables required to activate conda environment
# Activate conda environment
# Change workdir to analysis dir
# Add TTT_pipeline executables to path
TTT_BINDIR=/storage/TTT/bin
source $HOME/.bash_profile          
source activate proteotyping        
cd /storage/TTT/                    
export PATH=$TTT_BINDIR:$PATH  

# Run snakemake only if it isn't already currently running.
# flock creates a lockfile that, when open, indicates if the workflow in
# currently in progress. flock detects if the file is already opened and 
# the -n command makes it do nothing if snakemake is already running.
flock -n $LOCKFILE \
	nice -n $NICENESS \
	snakemake \
		--snakefile TTT_pipeline.snakefile \
		--configfile TTT_pipeline_snakemake_config.yaml \
		--cores $CORES \
		--keep-going \
        --resources mem=$MEM io=$IO \
		$1
