#!/bin/bash
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

# Set important paths and parameters
# This script expects a working Wine32 prefix in WINEPREFIX
export READW=/storage/TTT/bin/ReAdW.201510.xcalibur.exe
export WINEPREFIX=/storage/TTT/applications/wine32/
GNU_PARALLEL=/local/bin/parallel
NUM_CPU=20

# Check that enough command line arguments were specified
if [ $# -lt 1 ]
then
	echo "Usage: convert_raw_files_to_mzxml.sh <RAW_DIR> <MZXML_DIR>"
	exit
fi

export RAW_DIR=`readlink -f $1`
export MZXML_DIR=`readlink -f $2`

# If mzXML directory doesn't exist, create it
if [ ! -d $MZXML_DIR ]
then
	mkdir $MZXML_DIR
fi

# Perform RAW file conversions in parallel using GNU parallel
$GNU_PARALLEL -j $NUM_CPU 'if [ ! -e $MZXML_DIR/{/.}.mzXML.gz ]; 
	then
		echo "Converting {} to $MZXML_DIR/{/.}.mzXML.gz";
		wine $READW --centroid --nocompress --gzip {} $MZXML_DIR/{/.}.mzXML.gz;
	#else
	#	echo "Skipping {}"
	fi' ::: ${RAW_DIR}/*.raw

# Uncomment and use this code if GNU parallel is unavailable
#cd $RAW_DIR
#for RAW_FILE in *.raw; do 
#	BASE_NAME=${RAW_FILE%.raw}
#	# Symlink and convert RAW files without corresponding mzXML file.
#	if [ ! -e ${MZXML_DIR}/${BASE_NAME}.mzXML.gz ]
#	then
#		echo "Converting ${RAW_FILE} to $MZXML_DIR/$BASE_NAME.mzXML.gz"
#		wine $READW --centroid --nocompress --gzip $RAW_FILE ${MZXML_DIR}/${BASE_NAME}.mzXML.gz
#	fi
#done
