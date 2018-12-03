import logging
import typing

import urllib.request
import urllib.parse

import asyncio

import aiohttp

from ..types import RawCallbackType
from ..transport import TransportInterface


class AiohttpTransportInterface(TransportInterface):
    """
    Interface for HTTP transport layer.

    .. versionchanged:: 1.1
        This class was previously called `cfei.smap.transport.HttpTransportInterface`.
    """

    def __init__(
                self,
                url: typing.Text,
                key: typing.Text='',
                encoding: typing.Text='utf-8',
                buffer_size: int=2**16,
                max_concurrent_requests: int=10,
            ) -> None:
        """
        Create a `AiohttpTransportInterface` object.

        Args:
            :param url: sMAP archiver URL.
            :type: url: str
            :param key: sMAP archiver key.
            :type: key: str
            :param encoding: sMAP archiver text encoding (utf-8 or similar).
            :type: encoding: str
            :param buffer_size: buffer size for subscriptions.
            :type: buffer_size: int
            :param max_concurrent_requests: maximum amount of concurrent requests.
            :type: max_concurrent_requests: int
        """
        super(AiohttpTransportInterface, self).__init__()
        self.logger = logging.getLogger(__name__)

        self.base_url = urllib.parse.urlparse(url).geturl()
        self.query_url = urllib.parse.urljoin(self.base_url, '/api/query')
        self.subscribe_url = urllib.parse.urljoin(self.base_url, '/republish')
        self.post_url = urllib.parse.urljoin(self.base_url, '/add/' + key)

        self.buffer_size = buffer_size
        self.encoding = encoding
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def post_data(
                self,
                data: typing.Text
            ) -> None:
        """
        Post new data.

        :param data: data.
        :type data: str
        """

        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.post_url,
                    data=data.encode(self.encoding)
                ) as response:
                    self.logger.debug("Response status: %d", response.status)
                    if response.status != 200:
                        raise RuntimeError("Can't post data")

    async def fetch(
                self,
                query: typing.Text
            ) -> typing.Text:
        """
        Fetch data by query.

        :param query: Query.
        :type query: str

        :return: Query result.
        :rtype: JsonType
        """

        async with self.semaphore:
            self.logger.debug("Query: %s", query)
            data = query.encode(self.encoding)

            async with aiohttp.ClientSession(
                conn_timeout=60,
                read_timeout=None
            ) as session:
                async with session.post(
                    self.query_url,
                    data=data,
                    timeout=None
                ) as response:
                    self.logger.debug("Response status: %d", response.status)

                    # This could easily be implemented with stream.readline(), however,
                    # that method raises an exception if a line is longer than 2**16
                    # bytes.
                    stream = response.content
                    all_bytes = bytes()

                    while not stream.at_eof():
                        next_bytes = await stream.read(self.buffer_size)
                        all_bytes += next_bytes

                    text = all_bytes.decode(self.encoding)

                    if (response.status // 100) == 2:
                        # Success HTTP response
                        return text
                    else:
                        raise RuntimeError(
                            "HTTP Response Status: {}\n{}".format(
                                response.status,
                                text
                            )
                        )

    def synchronous_fetch(self, query: typing.Text) -> typing.Text:
        """
        Synchronously fetch data by query.

        :param query: Query.
        :type query: str


        :return: Query result.
        :rtype: JsonType
        """

        data = query.encode(self.encoding)
        response = urllib.request.urlopen(self.query_url, data)
        str_response = response.read().decode(self.encoding)
        return str_response

    async def subscribe(
                self,
                where: typing.Optional[typing.Text],
                callback: RawCallbackType,
                timeout: int=30
            ) -> None:
        """
        Subscribe to republish interface.

        The callback function will be called with new readings as soon as the
        archiver will republish them.

        :param where: Query text.
        :type where: str
        :param callback: Callback to process new readings.
        :type callback: CallbackType
        :param timeout: Connection timeout in seconds.
        :type timeout: int
        """

        self.logger.debug("Subscribing to %s", self.subscribe_url)
        async with aiohttp.ClientSession(
            read_timeout=None,
            conn_timeout=timeout
        ) as session:
            if where:
                self.logger.debug("Where: %s", where)
                data = where.encode(self.encoding)  # type: typing.Optional[bytes]
            else:
                data = None
            async with session.post(self.subscribe_url, data=data) as response:
                self.logger.debug("Response status: %d", response.status)
                stream = response.content
                await self._process_subscription_stream(stream, callback)

    async def _process_subscription_stream(
                self,
                stream: aiohttp.StreamReader,
                callback: RawCallbackType
            ) -> None:
        self.logger.debug('Processing subscription StreamReader')

        remaining_bytes = bytes()

        while not stream.at_eof():
            # This could easily be implemented with stream.readline(), however,
            # that method raises an exception if a line is longer than 2**16
            # bytes.

            next_bytes = await stream.read(self.buffer_size)
            chunks = (remaining_bytes + next_bytes).split(b'\n')

            for chunk in chunks[:-1]:
                try:
                    await self._process_chunk(chunk, callback)
                except Exception:
                    self.logger.error("Error processing chunk", exc_info=True)

            remaining_bytes = chunks[-1]

    async def _process_chunk(
                self,
                chunk: bytes,
                callback: RawCallbackType
            ) -> None:
        line = chunk.decode(self.encoding).strip()
        if len(line) > 0:
            await callback(line)
