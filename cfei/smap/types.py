from uuid import UUID
import typing

import pandas as pd


JsonType = typing.Any

RawCallbackType = typing.Callable[
    [typing.Text],
    typing.Awaitable[None]
]
"""
A raw callback is an `async` function (or a `@asyncio.coroutine` decorated
function) taking as arguments a string, i.e., a line returned by the
republish interface, and calls a callback with each update.
"""

CallbackType = typing.Callable[
    [UUID, typing.List],
    typing.Awaitable[None]
]
"""
A callback is an `async` function (or a `@asyncio.coroutine` decorated
function) taking as arguments a UUID and a list of readings, where each
reading is a 2-list [timestamp, value].
"""

SeriesCallbackType = typing.Callable[
    [UUID, pd.Series],
    typing.Awaitable[None]
]
"""
A series callback is an `async` function (or a `@asyncio.coroutine` decorated
function) taking as arguments a UUID and a time-series.
"""
