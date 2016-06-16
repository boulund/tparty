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

# Check that enough command line arguments were specified
if [ $# -lt 2 ]
then
	echo "Usage: convert_raw_to_mzxml.sh <PATH_TO_RAW> <PATH_TO_MZXML_OUT>"
	exit
fi

# Set important paths and parameters
# This script expects a working Wine32 prefix in WINEPREFIX
export READW=/storage/TTT/bin/ReAdW.201510.xcalibur.exe
export WINEPREFIX=/storage/TTT/applications/wine32/
export WINE=/usr/bin/wine

# Perform RAW file conversions in parallel using GNU parallel
echo "Converting $1 to ${2/.raw/}"
$WINE $READW --nocompress --gzip $1 ${2/.raw/}
