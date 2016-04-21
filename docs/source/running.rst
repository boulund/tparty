Running
=======
The TTT Proteotyping Pipeline can be run either by manually running each of the
steps, or it can be controlled automatically using `Snakemake`_.  The
automation ensures that each RAW input file is taken through all the required
steps to produce the final output. Together with the supplied
``snakemake_crontab_script.sh`` it can be used as a completely hands-off
automated way of analyzing proteomics samples.

.. note:: 
    The Snakemake workflow can only be run on Linux computers, as it depends on 
    some Linux command line features. 

.. _Snakemake: https://bitbucket.org/snakemake/snakemake/wiki/Home


Work directory
**************
The Snakemake workflow requires a work directory containing the following
folder structure::

    0.raw
    1.mzXML
    2.xml
    3.fasta
    4.blast8
    5.results

The reference data required to run the entire workflow is usually put in a
single directory (or symlinked there), but they can (in theory) be located
anywhere in the file system. The position of all the required files must be
specified in the ``TTT_pipeline_snakemake_config.yaml`` file. This file must be
specified on the command line when invoking the workflow.


Run the Snakemake workflow
**************************
To run the Snakemake workflow, ensure that a suitable Python/Conda environment
is activated in which all the proteotyping programs and scripts are available
in ``PATH``. The minimal command line required to start the workflow is this::

    snakemake --snakefile SNAKEFILE --configfile CONFIGFILE 

As the work directory is specified in the configfile, the command can in theory
be run anywhere in the file system.  It is recommended, however, that the
Snakemake workflow is invoked via the use of the included
``snakemkae_crontab_script.sh`` which sets some environment parameters to
ensure reliable operation. It uses the linux command ``flock`` to ensure that
only one instance of the workflow is ever run at the same time.


Automatic invokation via crontab
********************************
The workflow can be invoked automatically at set times using the Linux built-in
``crontab``.  To edit your personal user's crontab, type ``crontab -e`` at the
command prompt.  Add something like the following line to make the Snakemake
workflow check for new files to analyze three times daily (00:00, 12:00,
18:00)::

    0 0,12,18 * * * /bin/bash /PATH/TO/snakemake_crontab_script.sh

Make sure to modify the configfile (``TTT_pipeline_snakemake_config.yaml``) and
the crontab script file (``snakemake_crontab_script.sh``) to match your
environment.
