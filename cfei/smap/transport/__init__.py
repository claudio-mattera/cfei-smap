import typing

from ..types import RawCallbackType


class TransportInterface(object):
    """
    Interface for transport layer.
    """

    def __init__(self) -> None:
        super(TransportInterface, self).__init__()

    async def post_data(
                self,
                data: typing.Text
            ) -> None:
        """
        Post new data.

        :param data: data.
        :type data: str
        """
        raise RuntimeError('Not implemented')

    async def fetch(
                self,
                query: typing.Text
            ) -> typing.Text:
        """
        Fetch data by query.

        :param query: Query.
        :type query: str

        :return: Query result.
        :rtype: typing.Text
        """
        raise RuntimeError('Not implemented')

    def synchronous_fetch(self, query: typing.Text) -> typing.Text:
        """
        Synchronously fetch data by query.

        :param query: Query.
        :type query: str


        :return: Query result.
        :rtype: typing.Text
        """
        raise RuntimeError('Not implemented')

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
        raise RuntimeError('Not implemented')
