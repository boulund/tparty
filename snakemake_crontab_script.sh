#!/bin/bash
# Snakemake crontab script
# Fredrik Boulund 2016

source $HOME/.bash_profile          # Load environment variables required to activate conda environment
source activate proteotyping        # Activate conda environment
cd /storage/TTT/                    # Change workdir to analysis dir
export PATH=/storage/TTT/bin:$PATH  # Add TTT_pipeline executables to path
snakemake \
	--snakefile TTT_pipeline.snakefile \
	--configfile TTT_pipeline_snakemake_config.yaml \
	--cores 22
