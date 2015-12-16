#!/bin/bash
# Convert RAW files in RAW_DIR to mzXML files in MZXML_DIR
# Fredrik Boulund 2015

# Set path to ReAdW executable
# This script expects a working Wine32 prefix in WINEPREFIX
export READW=/home/boulund/research/TTT/src/ReAdW/bin/ReAdW.201510.xcalibur.exe
export WINEPREFIX=/home/boulund/research/TTT/wine32/

# Check if user specified DIR to be converted
#####
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
parallel -j 20 'if [ ! -e $MZXML_DIR/{/.}.mzXML.gz ]; 
	then
		echo "Converting {} to $MZXML_DIR/{/.}.mzXML.gz";
		wine $READW --centroid --nocompress --gzip {} $MZXML_DIR/{/.}.mzXML.gz;
	else
		echo "Skipping {}"
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
