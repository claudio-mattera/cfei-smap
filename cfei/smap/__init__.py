from json import dumps as json_dumps
from datetime import datetime
from uuid import UUID, uuid3
import logging
import heapq
from hashlib import md5

import pandas as pd
import typing

from .types import SeriesCallbackType
from .transport import TransportInterface
from .transport.aiohttp import AiohttpTransportInterface
from .validation import parse_and_validate
from .cache import (
    load_readings_from_cache,
    save_readings_to_cache,
    load_raw_from_cache,
    save_raw_to_cache,
)


class SmapInterface(object):
    """
    An interface to sMAP protocol.

    Each object has a local cache for metadata, so querying multiple times for
    a stream results in only one query for its metadata.
    """

    def __init__(
                self,
                transport_interface: TransportInterface,
                cache: bool=False,
                loose_validation: bool=False,
            ) -> None:
        """
        Create a `SmapInterface` object.

        :param transport_interface: transport interface.
        :type transport_interface: TransportInterface
        :param cache: set to True to use local cache.
        :type cache: bool
        :param cache: set to True to ignore JSON validation errors.
        :type cache: bool
        """

        super(SmapInterface, self).__init__()

        self.logger = logging.getLogger(__name__)

        self.transport_interface = transport_interface

        self.use_local_cache = cache
        self.loose_validation = loose_validation

        self.metadata_cache = {}  # type: typing.Dict[UUID, typing.Any]

        self.path_cache = {}  # type: typing.Dict[UUID, typing.Text]

    async def fetch_uuids(
                self,
                where: typing.Text,
            ) -> typing.Set[UUID]:
        """
        Query for UUIDs.

        Query the sMAP archiver for all streams that satisfy the `where`
        condition and return their UUIDs.

        :param where: Query `WHERE` condition.
        :type where: str

        :returns: The UUIDs.
        :rtype: set(UUID)
        """

        query = "select uuid where {}".format(where)
        output = await self.fetch_raw(query)
        results = parse_and_validate(
            output,
            'select_response_schema',
            self.loose_validation
        )
        return set([UUID(result['uuid']) for result in results])

    async def fetch_metadata(
                self,
                where: typing.Text,
            ) -> typing.Dict[UUID, typing.Any]:
        """
        Query for metadata.

        Query the sMAP archiver for all streams that satisfy the `where`
        condition and return their metadata.

        :param where: Query `WHERE` condition.
        :type where: str

        :returns: A mapping UUID -> metadata.
        :rtype: dict(UUID, object)
        """

        results = await self.fetch_everything(where)
        return dict(
            (uuid, everything['Metadata'])
            for uuid, everything in results.items()
        )

    async def fetch_properties(
                self,
                where: typing.Text,
            ) -> typing.Dict[UUID, typing.Any]:
        """
        Query for properties.

        Query the sMAP archiver for all streams that satisfy the `where`
        condition and return their properties.

        :param where: Query `WHERE` condition.
        :type where: str

        :returns: A mapping UUID -> properties.
        :rtype: dict(UUID, object)
        """

        results = await self.fetch_everything(where)
        return dict(
            (uuid, everything['Properties'])
            for uuid, everything in results.items()
        )

    async def fetch_everything(
                self,
                where: typing.Text,
            ) -> typing.Dict[UUID, typing.Any]:
        """
        Query for everything.

        Query the sMAP archiver for all streams that satisfy the `where`
        condition and return everything.

        :param where: Query `WHERE` condition.
        :type where: str

        :returns: A mapping UUID -> metadata.
        :rtype: dict(UUID, everything)
        """

        query = "select * where {}".format(where)
        output = await self.fetch_raw(query)
        results = parse_and_validate(
            output,
            'select_response_schema',
            self.loose_validation
        )
        return dict(
            (UUID(result['uuid']), result)
            for result in results
        )

    async def fetch_raw(
                self,
                query: typing.Text,
            ) -> typing.Text:
        """
        Query for raw query.

        Query the sMAP archiver using a custom query and return.

        :param where: Raw query.
        :type where: str

        :returns: Parsed JSON output.
        :rtype: Any
        """

        if self.use_local_cache:
            try:
                data = load_raw_from_cache(query)
            except Exception as exception:
                self.logger.debug("Could not load from cache: %s", str(exception))
                data = await self.transport_interface.fetch(query)
                save_raw_to_cache(data, query)
        else:
            data = await self.transport_interface.fetch(query)

        return data

    async def fetch_readings_intertwined(
                self,
                start: datetime,
                end: datetime,
                where: typing.Text,
                limit: int=-1,
                streamlimit: int=10000,
            ) -> pd.Series:
        """
        Query for readings and return a single stream.

        Query the sMAP archiver for all readings between `start` and `end` for
        all streams that satisfy the `where` condition. The results are
        intertwined.

        :param start: Query start time.
        :type start: datetime
        :param end: Query end time.
        :type end: datetime
        :param where: Query `WHERE` condition.
        :type where: str
        :param limit: Maximum number of readings (-1 for unlimited)
        :type limit: int
        :param streamlimit: Maximum number of streams
        :type streamlimit: int

        :returns: Intertwined series.
        :rtype: pd.Series

        .. warning :: When :code:`limit` is equal to -1 the returned
            streams are actually limited to one million readings (possibly
            depending on the server implementation). Using a higher value for
            :code:`limit` works correctly.
        """
        results = await self.fetch_readings(
            start, end, where, limit, streamlimit
        )
        return intertwine_series(list(results.values()))

    async def fetch_readings(
                self,
                start: datetime,
                end: datetime,
                where: typing.Text,
                limit: int=-1,
                streamlimit: int=10000,
            ) -> typing.Dict[UUID, pd.Series]:
        """
        Query for readings and return by UUID.

        Query the sMAP archiver for all readings between `start` and `end` for
        all streams that satisfy the `where` condition. The results are
        returned by UUID.

        :param start: Query start time.
        :type start: datetime
        :param end: Query end time.
        :type end: datetime
        :param where: Query `WHERE` condition.
        :type where: str
        :param limit: Maximum number of readings (-1 for unlimited)
        :type limit: int
        :param streamlimit: Maximum number of streams
        :type streamlimit: int

        :returns: A mapping UUID -> values.
        :rtype: dict(UUID, pd.Series)

        .. warning :: When :code:`limit` is equal to -1 the returned
            streams are actually limited to one million readings (possibly
            depending on the server implementation). Using a higher value for
            :code:`limit` works correctly.
        """

        if self.use_local_cache:
            try:
                data = load_readings_from_cache(
                    start, end, where, limit, streamlimit
                )
            except Exception as exception:
                self.logger.debug("Could not load from cache: %s", str(exception))
                data = await self._fetch_readings(
                    start,
                    end,
                    where,
                    limit,
                    streamlimit
                )
                save_readings_to_cache(
                    data,
                    start,
                    end,
                    where,
                    limit,
                    streamlimit,
                )

        else:
            data = await self._fetch_readings(
                start,
                end,
                where,
                limit,
                streamlimit
            )

        if limit == -1:
            for uuid, stream in data.items():
                if len(stream) == 1000000:
                    self.logger.warn(
                        "UUID %s has exactly one million readings, "
                        "if limit was set to -1 they could be incomplete",
                        uuid
                    )

        # Cached data might be larger than the requested period, truncate it.
        def truncate(stream: pd.Series) -> pd.Series:
            stream = stream[stream.index >= start]
            stream = stream[stream.index <= end]
            return stream

        return dict(
            (uuid, truncate(stream))
            for uuid, stream in data.items()
        )

    async def _fetch_readings(
                self,
                start: datetime,
                end: datetime,
                where: typing.Text,
                limit: int,
                streamlimit: int
            ) -> typing.Dict[UUID, pd.Series]:

        query = (
            "select data in ({start}, {end}) "
            "limit {limit} streamlimit {streamlimit} "
            "where {where}").format(
                start=_to_milli_timestamp(start),
                end=_to_milli_timestamp(end),
                limit=limit,
                streamlimit=streamlimit,
                where=where,
            )

        # Do not use self.fetch_raw()
        # That method uses a general local cache, while for data it is not
        # necessary to match the entire query, a larger cache can be used as
        # well.
        output = await self.transport_interface.fetch(query)
        results = parse_and_validate(
            output,
            'select_response_schema',
            self.loose_validation
        )
        return dict(
            (
                UUID(result['uuid']),
                _parse_readings(UUID(result['uuid']), result['Readings'])
            )
            for result in results
        )

    async def fetch_latest_readings(
                self,
                where: typing.Text,
                limit: int=1,
                streamlimit: int=10000,
                instant: typing.Optional[datetime]=None
            ) -> typing.Dict[UUID, pd.Series]:
        """
        Query for readings and return by UUID.

        Query the sMAP archiver for all the readings before current or
        specified instant for all streams that satisfy the `where` condition.
        The results are returned by UUID.

        :param where: Query `WHERE` condition.
        :type where: str
        :param limit: Maximum number of readings (-1 for unlimited)
        :type limit: int
        :param streamlimit: Maximum number of streams
        :type streamlimit: int
        :param instant: Instant (if `None`, current instant is used)
        :type instant: datetime

        :returns: A mapping UUID -> values.
        :rtype: dict(UUID, pd.Series)
        """

        if instant is None:
            query = (
                "select data before now "
                "limit {limit} streamlimit {streamlimit} "
                "where {where}").format(
                    limit=limit,
                    streamlimit=streamlimit,
                    where=where,
                )
        else:
            query = (
                "select data before {instant} "
                "limit {limit} streamlimit {streamlimit} "
                "where {where}").format(
                instant=_to_milli_timestamp(instant),
                    limit=limit,
                    streamlimit=streamlimit,
                    where=where,
                )
        output = await self.transport_interface.fetch(query)
        results = parse_and_validate(
            output,
            'select_response_schema',
            self.loose_validation
        )
        return dict(
            (
                UUID(result['uuid']),
                _parse_readings(UUID(result['uuid']), result['Readings'])
            )
            for result in results
        )

    async def subscribe(
                self,
                where: typing.Optional[typing.Text],
                callback: SeriesCallbackType,
                timeout: int=30
            ) -> None:
        """
        Subscribe to sMAP republish interface.

        The callback function will be called with new readings as soon as the
        archiver will republish them.

        Args:
        :param where: Query text.
        :type where: str
        :param callback: Callback to process new readings.
        :type callback: SeriesCallbackType
        :param timeout: Connection timeout in seconds.
        :type timeout: int
        """

        async def raw_callback(
                    line: typing.Text
                ) -> None:
            payloads = parse_and_validate(
                line,
                'subscribe_response_schema',
                self.loose_validation
            )
            for payload in payloads.values():
                uuid = UUID(payload['uuid'])
                readings = payload['Readings']
                series = _parse_readings(uuid, readings)

                await callback(uuid, series)

        return await self.transport_interface.subscribe(where, raw_callback, timeout)

    async def post_readings(
                self,
                readings: typing.Union[typing.Dict[UUID, pd.Series], typing.Tuple[UUID, pd.Series]],
            ) -> None:
        """
        Post new readings to existing streams.

        The specified streams' paths will be fetched and cached before posting
        the readings. All streams must, therefore, exist beforehand.

        :param readings: Either a dictionary {UUID: series} or a pair (UUID, pd.Series).
        :type readings: dict|pd.Series
        """

        if isinstance(readings, dict):
            streams = readings  # type: typing.Dict[UUID, pd.Stream]
        elif isinstance(readings, tuple):
            streams = {
                readings[0]: readings[1]
            }

        unknown_uuids = set(
            uuid
            for uuid in streams.keys()
            if uuid not in self.path_cache
        )

        if len(unknown_uuids) > 0:
            self.logger.debug(
                "Unknown UUIDs %s, getting their path...",
                ', '.join(map(str, unknown_uuids))
            )
            query = "select Path where {}".format(
                ' or '.join(
                    "uuid = '{}'".format(uuid)
                    for uuid in unknown_uuids
                )
            )

            output = await self.fetch_raw(query)
            results = parse_and_validate(
                output,
                'select_response_schema',
                self.loose_validation
            )
            for result in results:
                uuid = UUID(result['uuid'])
                path = result['Path']
                self.logger.debug("Path for UUID %s is %s", uuid, path)
                self.path_cache[uuid] = path

        payload = dict()

        for uuid, stream in streams.items():
            try:
                path = self.path_cache[uuid]
            except KeyError:
                raise RuntimeError(
                    "Stream with UUID {} does not exist, its path is unknown".format(
                        uuid
                    )
                )

            payload[path] = _make_update_payload(
                uuid,
                stream=stream
            )

        data = json_dumps(payload)
        self.logger.debug("Payload: %s", data)

        await self.transport_interface.post_data(data)

    async def post_data(
                self,
                stream: pd.Series,
                uuid: UUID,
                source_name: typing.Text,
                path: typing.Text,
                metadata: typing.Optional[typing.Dict]=None,
                properties: typing.Optional[typing.Dict]=None,
            ) -> None:
        """
        Post new readings to a stream.

        :param streams: New readings.
        :type streams: pd.Series
        :param uuid: Stream's UUID.
        :type uuid: UUID
        :param source_name: Stream's source name.
        :type source_name: str
        :param path: Stream's path.
        :type path: str
        :param metadata: Stream's metadata
        :type metadata: dict
        :param properties: Stream's properties
        :type properties: dict
        """

        if metadata is None:
            metadata = dict()

        metadata = metadata.copy()
        metadata['SourceName'] = source_name

        payload = {
            path: _make_update_payload(
                uuid,
                stream=stream,
                metadata=metadata,
                properties=properties
            )
        }
        data = json_dumps(payload)
        self.logger.debug("Payload: %s", data)

        await self.transport_interface.post_data(data)

    async def _update_metadata_cache_for(
                self,
                uuids: typing.Set[UUID]
            ) -> None:
        where = ' or '.join("uuid = '{}'".format(str(uuid)) for uuid in uuids)
        results = await self.fetch_metadata(where)
        for uuid in uuids:
            self.metadata_cache[uuid] = results[uuid]


def _make_update_payload(
            uuid: UUID,
            stream: typing.Optional[pd.Series]=None,
            metadata: typing.Optional[typing.Dict]=None,
            properties: typing.Optional[typing.Dict]=None,
        ) -> typing.Dict:
    payload = {
        'uuid': str(uuid),
    }  # type: typing.Dict[typing.Text, typing.Any]

    if stream is not None:
        readings = list(map(lambda a: list(a), zip(
            [_to_milli_timestamp(ts) for ts in stream.index],
            [float(v) for v in stream.values]
        )))
        payload['Readings'] = readings
    else:
        payload['Readings'] = []
    if properties is not None:
        payload['Properties'] = properties
    if metadata is not None:
        payload['Metadata'] = metadata
    return payload


def _parse_readings(
        uuid: UUID,
        readings: typing.List[typing.List]
        ) -> pd.Series:
    if len(readings) == 0:
        timestamps = []  # type: typing.List[int]
        values = []  # type: typing.List[float]
    else:
        timestamps, values = zip(*readings)

    index = pd.to_datetime(timestamps, unit='ms', utc=True)
    return pd.Series(values, index=index, name=str(uuid))


def _to_milli_timestamp(date: datetime) -> int:
    if date.tzinfo is None:
        raise RuntimeError(
            "Cannot convert a timezone-naive datetime to a timestamp"
        )
    return 1000 * int(date.timestamp())


class SmapAiohttpInterface(SmapInterface):
    """
    An interface to sMAP protocol over HTTP.

    .. versionadded:: 1.1
    """

    def __init__(
                self,
                url: typing.Text,
                key: typing.Text='',
                encoding: typing.Text='utf-8',
                buffer_size: int=2**16,
                max_concurrent_requests: int=10,
                cache: bool=False
            ) -> None:
        """
        Create a `SmapAiohttpInterface` object.

        All arguments are passed to `cfei.smap.transport.AiohttpTransportInterface`.

        :param url: sMAP archiver URL.
        :type url: str
        :param key: sMAP archiver key.
        :type key: str
        :param encoding: sMAP archiver text encoding (utf-8 or similar).
        :type encoding: str
        :param buffer_size: buffer size for subscriptions.
        :type buffer_size: int
        :param max_concurrent_requests: maximum amount of concurrent requests.
        :type max_concurrent_requests: int
        :param cache: set to True to use local cache.
        :type cache: bool
        """
        super(SmapAiohttpInterface, self).__init__(
            AiohttpTransportInterface(
                url,
                key,
                encoding,
                buffer_size,
                max_concurrent_requests,
            ),
            cache=cache
        )


class SmapHttpInterface(SmapInterface):
    """
    An interface to sMAP protocol over HTTP.

    .. deprecated:: 1.1
        Use :class:`SmapAiohttpInterface` instead.
    """

    def __init__(
                self,
                url: typing.Text,
                key: typing.Text='',
                encoding: typing.Text='utf-8',
                buffer_size: int=2**16,
                max_concurrent_requests: int=10,
                cache: bool=False
            ) -> None:
        """
        Create a `SmapHttpInterface` object.

        All arguments are passed to `cfei.smap.transport.AiohttpTransportInterface`.

        :param url: sMAP archiver host name.
        :type url: str
        :param key: sMAP archiver key.
        :type key: str
        :param encoding: sMAP archiver text encoding (utf-8 or similar).
        :type encoding: str
        :param buffer_size: buffer size for subscriptions.
        :type buffer_size: int
        :param max_concurrent_requests: maximum amount of concurrent requests.
        :type max_concurrent_requests: int
        :param cache: set to True to use local cache.
        :type cache: bool
        """
        super(SmapHttpInterface, self).__init__(
            AiohttpTransportInterface(
                url,
                key,
                encoding,
                buffer_size,
                max_concurrent_requests,
            ),
            cache=cache
        )


def intertwine_series(serieses: typing.List[pd.Series]) -> pd.Series:
    '''
    Convert a list of time-series to a single time-series, such that readings
    are in order

    :param series: List of time-series.
    :type series: typing.List[pd.Series]
    :param uuids: List of uuids.
    :type uuids: typing.List[UUID]

    :returns: A new intertwined time-series.
    :rtype: pd.Series
    '''

    lists = [
        [
            (index, value)
            for index, value in series.iteritems()
        ]
        for series in serieses
        if len(series) > 0
    ]

    if len(lists) == 0:
        return pd.Series()

    index, values = zip(*heapq.merge(*lists))

    series = pd.Series(values, index=index)
    series = series[~series.index.duplicated(keep='first')]
    return series


def generate_uuid_as_in_java(
            source_name: typing.Text,
            path: typing.Text
        ) -> UUID:
    '''
    Generate a UUID from source name and path

    This function has the same implementation of the Java library, therefore,
    with same inputs it will generate the same UUID.

    :param source_name: Source name
    :type source_name: typing.Text
    :param path: Path.
    :type path: typing.Text

    :returns: A UUID.
    :rtype: UUID
    '''
    class NULL_NAMESPACE:
        bytes = md5((source_name + path).encode('utf-8')).digest()

    return uuid3(typing.cast(UUID, NULL_NAMESPACE), '')
