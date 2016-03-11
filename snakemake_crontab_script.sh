#!/bin/bash
# Snakemake crontab script
# Fredrik Boulund 2016

# Lockfile used to indicate if snakemake workflow is currently running
export LOCKFILE=/storage/TTT/.TTT_snakemake.lock

# Load environment variables required to activate conda environment
source $HOME/.bash_profile          
# Activate conda environment
source activate proteotyping        
# Change workdir to analysis dir
cd /storage/TTT/                    
# Add TTT_pipeline executables to path
export PATH=/storage/TTT/bin:$PATH  

# Run snakemake only if it isn't already currently running.
# flock creates a lockfile that, when open, indicates if the workflow in
# currently in progress. flock detects if the file is already opened and 
# the -n command makes it do nothing if snakemake is already running.
flock -n $LOCKFILE \
	snakemake \
		--snakefile TTT_pipeline.snakefile \
		--configfile TTT_pipeline_snakemake_config.yaml \
		--cores 22 \
		$1
