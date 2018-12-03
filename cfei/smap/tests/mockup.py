import typing

from cfei.smap.types import RawCallbackType
from cfei.smap.transport import TransportInterface


class DummyTransportInterface(TransportInterface):
    """docstring for DummyTransportInterface"""
    def __init__(
                self,
                result: typing.Text,
            ) -> None:
        super(DummyTransportInterface, self).__init__()

        self.result = result

    async def post_data(
                self,
                data: typing.Text
            ) -> None:
        self.received_post_data = data

    async def fetch(
                self,
                query: typing.Text
            ) -> typing.Text:

        self.received_fetch_query = query

        return self.result

    def synchronous_fetch(self, query: typing.Text) -> typing.Text:
        raise RuntimeError('Not implemented')

    async def subscribe(
                self,
                where: typing.Optional[typing.Text],
                callback: RawCallbackType,
                timeout: int=30
            ) -> None:
        raise RuntimeError('Not implemented')
