
*********
Internals
*********

.. toctree::
   :maxdepth: 2
   :caption: Contents:


=========
Structure
=========

The library consists of a `SmapInterface` class that defines the main interface over sMAP.
This class uses an abstract class `TransportInterface` that defines primitives to send and retrieve data over HTTP.
Splitting the transport implementation from its interface allows to use this library with multiple backends.
The only supported backend at the moment is the aiohttp_ library, plus a mockup backend used for testing.



=======
Caching
=======

The library supports caching time-series and metadata on the local machine, to reduce fetch time, network traffic and server load.
When a query is executed for the first time, a filename is obtained by hashing its where-clause, and the query results are saved to such file.
The following times the same query is executed, the results are taken from the local cached file.

The cache contains also the selected period, so that queries with same where-clause but different periods can use the cache, provided that the requested period is contained in the cached period.
Other parameters, such as limits, are also stored in cache, and if they do not match, they invalidate the cache.

Local cache is disabled by default, and can enabled by passing ``cache=True`` to the ``SmapInterface`` constructor.
The cache directory is obtained from appdirs_ library, and is usually located at:

- ``/home/USERNAME/.cache/sMAP-Python`` on Linux/Unix
- ``C:\\Users\\USERNAME\\AppData\\Local\\Acme\\sMAP-Python\\Cache`` on Windows

Invalidated cache files are deleted and re-created, but local cache is otherwise never deleted.
In case it becomes too large, it should be manually deleted.



=================
Schema Validation
=================

sMAP server returns results through JSON encoding.
This library optionally checks whether the returned JSON payloads respect the expected jsonschema_.
This can be useful to diagnose a faulty server implementation.


.. _aiohttp: https://aiohttp.readthedocs.io/
.. _appdirs: https://pypi.org/project/appdirs/
.. _jsonschema: https://json-schema.org/
