Installation
============
TTT Proteotyping Pipeline consists of several steps:

 * raw to mzXML conversion with _`ReAdW`.
 * peptide identification with _`X!Tandem`.
 * X!Tandem xml output to FASTA conversion with _`convert_tandem_xml_2_fasta.py`.
 * Peptide to reference database alignment with _`BLAT`.
 * Antibiotic resistance detection with _`Proteotyping`.
 * Taxonomic composition estimation with _`Proteotyping`.
 * Listing distinct/unique proteins in X!Tandem output with _`create_unique_protein_list.py`.

ReAdW, X!Tandem, and BLAT are external programs. This documentation will give
brief instructions on how to install and use them together with TTT
Proteotyping Pipeline. The Python programs are a part of this Python package,
available in the ``TTT_proteotyping_pipeline`` folder
in the repository. 

The steps can be run manually, or preferably via the included Snakemake script.


Download the code
*****************
To download the code, clone the repository::

    $ hg clone https://bitbucket.org/chalmersmathbioinformatics/TTT_proteotyping_pipeline

This will clone the entire repository to a folder called `TTT_proteotyping_pipeline` in
your current directory.


ReAdW
*****
ReAdW is meant to be run under Windows, but can be run under Linux using Wine,
see instructions below. Running ReAdW in Wine requires a Linux system with a
working 32-bit Wine installation. 

.. note:: 
    It is important that you can run a 32-bit Wine installation, as ReAdW
    cannot be run under a 64-bit only installation of Wine. As of this writing,
    32-bit Wine is only available for RedHat Enterprise Linux 6 and below.
    Support for 32-bit Wine was apparently removed in RHEL 7. 


Get ReAdW
---------
ReAdW can be downloaded from the `ReAdW Github repository`_. Either clone the
entire repository or download the binary suitable for your system. Note the
information about the dependencies on three Windows DLL files:
``XRawfile2.dll``, ``fileio.dll``, ``fregistry.dll``. These files are **NOT**
supplied with this pipeline. 

.. _ReAdW Github repository: https://github.com/PedrioliLab/ReAdW


Create a 32-bit Wine prefix
---------------------------
1. Install Wine. It is important that a 32-bit version of Wine is installed,
   this normally means packages named ``<package>.i686`` instead of
   ``<package>.x86_64``.  In RHEL/CentOS it can be installed like this::
    
    yum install wine

2. Create a Win32 prefix from which to run ReAdW. Make sure to set and export
   ``WINEARCH=win32`` during the creation of the wine prefix. Modify the
   command below to a path of your choice. Note that this step likely requires
   working X11-forwarding::

    export WINEARCH=win32
    export WINEPREFIX=/path/to/your/desired/wineprefix
    winecfg
  
   Click OK in any configuration windows that pop up.

3. Download `winetricks` to install the required Visual Studio C++ runtimes.
   ``vcrun2010`` is required for ReAdW and ``vcrun2008`` is required for the
   Thermo DLL's. Again, note that this step requires X11-forwarding to be
   enabled::

    wget https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks
    sh winetricks vcrun2010 vcrun2008

  Click through any installation prompts that pop up, and after they complete, finish by
  registering XRawfile2.dll in your wine prefix::

   wine regsvr32 XRawfile2.dll


Running ReAdW
-------------
Make sure to set the ``WINEPREFIX`` environment variable to the correct path
(same directory you specified when creating the 32 bit wine prefix), then run ReAdW from
your Linux command prompt via Wine::

    export WINEPREFIX=/path/to/your/desired/wineprefix
    wine /path/to/ReAdW.201510.xcalibur.exe [options] /path/to/sample.raw

Now it should run. 


X!Tandem
********
Download and install X!Tandem according to the instructions on the `X!Tandem homepage`_.
To run a sample in X!Tandem, several xml-files must be prepared. There is a Python program 
in TTT Proteotyping Pipeline called ``run_xtandem.py`` that will automatically create the 
required input files and run X!Tandem for you. It makes it very easy to use X!Tandem::

    run_xtandem.py --output OUTFILE --db /PATH/TO/FASTA --threads N --xtandem /PATH/TO/TANDEM.EXE

.. _X!Tandem homepage: http://www.thegpm.org/TANDEM/instructions.html


