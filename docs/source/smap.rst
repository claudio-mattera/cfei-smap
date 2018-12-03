
**********************************
CFEI Python sMAP Command Line Tool
**********************************


========
SYNOPSIS
========

::
    usage: smap [-h] [-v] --url URL [--plot] [--plot-markers] [--csv]
                [--start DATETIME] [--end DATETIME]
                WHERE



===========
DESCRIPTION
===========

*smap* is a command line tool to fetch data from a sMAP server.


=======
OPTIONS
=======

---------------
General options
---------------

``-h``, ``--help`` Show documentation

``-v`` Increase verbosity


---------------------
sMAP archiver options
---------------------

``--url`` sMAP archiver URL


------------
Data options
------------

``--start`` Initial time [default: 24h ago]

``--end`` Final time [default: now]


--------------
Output options
--------------

``--csv`` Print results to stdout in CSV format

``--plot`` Plot results

``--plot-markers`` Show plot markers


===========
EXAMPLES
===========

The following command plots the specified UUID over the past 24h::

    smap --url http://localhost --plot "uuid='12345678-1234-1234-1234-12345678abcd'"
