CFEI sMAP Python Library
===========

This is a Python 3 library to interface to [sMAP] archivers.
It uses the [asyncio] framework to connect to the archiver, and it returns [pandas] data-frames and time-series.

Documentation available at https://sdu-cfei.github.io/cfei-smap/


Features
----

*   **Fetching historical data**.
    The user specifies a time interval and a query, and the library returns all time-series that satisfy the query.

    The user can also request a single time-series.
    In that case, all resulting time-series will be intertwined to generate a single one.
    This is useful when time-series are split in multiple streams, e.g., in case of gateway jumps.

*   **Subscribing to real-time data**.
    The user specifies a query and a callback, and the library will call the callback whenever a new reading is available.

    Since the library supports IO concurrency, the application can perform other operations, while waiting for new data.

*   **Posting data**.
    The users specifies a set of readings, a source name, a path and a UUID.
    It can optionally specify properties and metadata.

    A simpler interface is available when posting data to existing streams.
    The user specifies only UUIDs and readings, and the library will transparently retrieve and cache source names and paths.

*   **Concurrent requests**.
    The user can instantiate multiple concurrent requests to the sMAP archiver, the library (or, better, the asyncio framework) will execute them in parallel.

    A parameter defines how many concurrent requests to execute (default: 10) to not overload the sMAP archiver.
    Any further request will be transparently enqueued and executed as soon as a slot is free.

*   **Local caching**.
    Readings can be cached on the local machine.
    The library can detect when the requested time interval (or larger) is available locally.
    This saves execution time, network traffic and server load.
    If the cache does not correspond to the user's query, it is invalidated and data is automatically fetched from the server.

    *Note*: the library cannot detect when readings were replaced/added on the server.
    Cache should be used only for immutable historical data, not for data that can change.

*   **Command line tool**.
    The tool can be used to quickly plot single time-series data, or to export to CSV files.


Installation
----

The library is available as three different packages:

-   Debian package, usable on Debian/Ubuntu and derivatives (anything that uses `apt`/`apt-get`).
    Install it with the following command (possibly prepended with `sudo`).

        dpkg -i /path/to/python3-cfei-smap_1.2.0-1_all.deb

-   Python wheel package, usable on Windows and almost every system with a Python 3 distribution.
    Install it with the following command (possibly prepended with `sudo`, or passing the `--user` option).

        pip3 install /path/to/cfei_smap-1.1-py3-none-any.whl

-   Tarball source package.
    It can be used by maintainers to generate a custom package.


Usage
----

### General Instructions

This library uses the [asyncio] framework, and returns [pandas] data-frames and time-series.

Most of the features are available as member functions of objects implementing `SmapInterface`.
Clients should first create one of the concrete classes, e.g., `SmapAiohttpInterface`, and then call its methods.

~~~~python
from cfei.smap import SmapAiohttpInterface

...

smap = SmapAiohttpInterface("http://hostname.com:8079")

await smap.fetch_readings(...)
~~~~


### Important Note about Timezones

Whenever using time-series data, proper care should be taken to correctly store and represent timezones.
Unfortunately, many tools lack support for timezones, and many users assume localtime is good enough.
This often results in issues when sharing time-series with other persons, or storing them in databases.
It also causes problems at daylight saving time changes, when the time offset of a timezone changes.
Therefore, this library enforces using timezone-aware datetimes.
Whenever a date is expected, it *must* be a timezone-aware datetime object in UTC, otherwise an exception will be generated.

This could make things more complicate and cumbersome when users are interested in localtime dynamics, such as occupancy behaviour or price trends, because they have to manually convert to and from UTC.
An example on how to convert back and forth from UTC is included in :ref:`timezones`.


### Fetching Data

To fetch data from sMAP, the caller must specify the interval as a pair of `datetime` objects and a *where* query.

~~~~python
from datetime import datetime

import pytz

from cfei.smap import SmapAiohttpInterface


async def main():
    smap = SmapAiohttpInterface("http://hostname.com:8079")

    start = pytz.UTC.localize(datetime(2018, 1, 1, 10, 15))
    end = pytz.UTC.localize(datetime(2018, 1, 8, 4, 5))

    where = (
        "Metadata/Location/Building = 'MyBuilding' and "
        "Metadata/Location/Room = 'MyRoom' and "
        "Metadata/Location/Media = 'air' and "
        "Metadata/Location/Media = 'co2'"
    )

    readings_by_uuid = await smap.fetch_readings(start, end, where)

    # It returns a dict[UUID, pd.Series]

    readings = await smap.fetch_readings_intertwined(start, end, where)

    # It returns a single pd.Series obtained by intertwining all the results
~~~~

#### Note

If there are readings at `start` and `end` instants, the returned time-series will be defined on the *closed* interval [`start`, `end`].
Otherwise, which is a more common scenario, the returned time-series will be defined on the *open* interval ]`start`, `end`[.


### Posting Data

Users can post both data (a sequence of readings, i.e., timestamp, value pairs) and metadata (a set of key, value pairs) to any number of sMAP streams.

There are two options to post data to a stream:

1.  Providing *path*, *source name* and *UUID* (and optionally metadata and properties).
    This option can be used to create non-existing streams.

        from datetime import datetime
        from uuid import UUID

        import pandas as pd

        from cfei.smap import SmapAiohttpInterface

        async def main():
            series = pd.Series(...)
            uuid = UUID(...)

            await smap.post_data(series, uuid, source_name, path)

2.  Providing only the *UUIDs*.
    In this case the library will retrieve and cache the corresponding *path* and *source name*, before actually posting data.
    This option is only available if the streams already exist.

        from datetime import datetime
        from uuid import UUID

        import pandas as pd

        from cfei.smap import SmapAiohttpInterface

        async def main():
            series = pd.Series(...)
            uuid = UUID(...)

            await smap.post_readings({
              uuid: series
            })


### Subscribing to real-time data

Users can subscribe to sMAP, and be notified of every new available reading.

~~~~python
from uuid import UUID

from cfei.smap import SmapAiohttpInterface


async def callback(uuid, series):
    for timestamp, value in series.iteritems():
        print("{}: {}".format(timestamp, value))


async def main():
    smap = SmapAiohttpInterface("http://hostname.com:8079")

    where = (
        "Metadata/Location/Building = 'MyBuilding' and "
        "Metadata/Location/Room = 'MyRoom' and "
        "Metadata/Location/Media = 'air' and "
        "Metadata/Location/Media = 'co2'"
    )

    await smap.subscribe(where, callback)
~~~~


### Enabling Local Cache

Pass `cache=True` to the `SmapInterface` constructor to enable local cache.

~~~~python
from cfei.smap import SmapAiohttpInterface


async def main():
    smap = SmapAiohttpInterface("http://hostname.com:8079", cache=True)

    # The first time data are fetched from server and cached locally.
    await smap.fetch_readings(start, end, where)

    # The second time they are loaded from local cache.
    await smap.fetch_readings(start, end, where)

    # This interval is strictly contained in the previous one, so data can
    # still be loaded from local cache.
    await smap.fetch_readings(
        start + timedelta(days=3),
        end - timedelta(days=2),
        where
    )

    # This interval is *NOT* strictly contained in the previous one, cache
    # will be invalidated and data will be fetched from server.
    await smap.fetch_readings(
        start - timedelta(days=3),
        end,
        where
    )
~~~~


### Note about *asyncio*

This library uses the *asyncio* framework.
This means that all functions and methods are actually coroutines, and they need to be called accordingly.
The caller can retrieve the event loop, and explicitly execute a coroutine

~~~~python
import asyncio

loop = asyncio.get_event_loop()

result = loop.run_until_complete(
    smap.method(arguments)
)
~~~~

Otherwise, if the caller is itself a coroutine, it can use the corresponding syntax in Pyhton 3.5+

~~~~python
async def external_coroutine():
    result = await smap.method(arguments)
~~~~


Command Line Utility
----

This library includes a command line utility named `smap`, which can be used to retrieve and plot data from sMAP archiver.

~~~~
usage: smap [-h] [-v] --url URL [--plot] [--plot-markers] [--csv]
            [--start DATETIME] [--end DATETIME]
            WHERE

Fetch data from sMAP

positional arguments:
  WHERE             sMAP query where

optional arguments:
  -h, --help        show this help message and exit
  -v, --verbose     increase output
  --url URL         sMAP archiver URL
  --plot            plot results
  --plot-markers    show plot markers
  --csv             print results to stdout in CSV format
  --start DATETIME  initial time (default: 24h ago)
  --end DATETIME    final time (default: now)
~~~~

For instance, to export a single time-series to CSV file:

~~~~bash
smap --url http://hostname.com:8079 "uuid = '12345678-1234-1234-1234-12345678abcd'" \
    --start 2018-01-17T00:00:00Z --csv -vv > output.csv
~~~~


[sMAP]: https://pythonhosted.org/Smap/en/2.0/archiver.html

[asyncio]: https://docs.python.org/3/library/asyncio.html

[pandas]: https://pandas.pydata.org/
