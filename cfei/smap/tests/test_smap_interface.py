from uuid import UUID
import json
from datetime import datetime, timezone
import asyncio

import pandas as pd
from pandas.util.testing import assert_series_equal

from cfei.smap import SmapInterface
from .mockup import DummyTransportInterface


def test_fetch_readings() -> None:
    loop = asyncio.get_event_loop()

    start = datetime(2017, 1, 1, tzinfo=timezone.utc)
    end = datetime(2017, 10, 1, tzinfo=timezone.utc)
    where = "Metadata/Location/Building = 'Some Building'"

    uuid = UUID('12345678-1234-5678-9abc-123456789abc')

    expected_query = (
        "select data in (1483228800000, 1506816000000) "
        "limit -1 streamlimit 10000 "
        "where Metadata/Location/Building = 'Some Building'"
    )

    transport_result = [
        {
            'uuid': str(uuid),
            'Readings': [
                [1483228800000, 5.0],
                [1485907200000, 8.0],
                [1488326400000, 12.0],
                [1491004800000, -5.3]
            ]
        }
    ]

    expected_result = pd.Series(
        [5.0, 8.0, 12.0, -5.3],
        index=pd.to_datetime(
            [
                datetime(2017, 1, 1, tzinfo=timezone.utc),
                datetime(2017, 2, 1, tzinfo=timezone.utc),
                datetime(2017, 3, 1, tzinfo=timezone.utc),
                datetime(2017, 4, 1, tzinfo=timezone.utc),
            ],
            utc=True
        ),
        name=str(uuid)
    )

    transport_interface = DummyTransportInterface(json.dumps(transport_result))
    smap = SmapInterface(transport_interface)

    result = loop.run_until_complete(
        smap.fetch_readings(start, end, where)
    )

    assert transport_interface.received_fetch_query == expected_query

    assert len(result) == 1

    assert list(result.keys())[0] == uuid

    assert_series_equal(list(result.values())[0], expected_result)


def test_post_data() -> None:
    loop = asyncio.get_event_loop()

    uuid = UUID('12345678-1234-5678-9abc-123456789abc')
    series = pd.Series(
        [5.0, 8.0, 12.0, -5.3],
        index=pd.to_datetime(
            [
                datetime(2017, 1, 1, tzinfo=timezone.utc),
                datetime(2017, 2, 1, tzinfo=timezone.utc),
                datetime(2017, 3, 1, tzinfo=timezone.utc),
                datetime(2017, 4, 1, tzinfo=timezone.utc),
            ],
            utc=True
        ),
        name=str(uuid)
    )
    source_name = 'My Source Name'
    path = '/some/path'
    metadata = {
        'Location': {
            'Building': 'Some Building'
        }
    }

    expected_data = {
        path: {
            'uuid': str(uuid),
            'Readings': [
                [1483228800000, 5.0],
                [1485907200000, 8.0],
                [1488326400000, 12.0],
                [1491004800000, -5.3]
            ],
            'Metadata': {
                'SourceName': source_name,
                'Location': {
                    'Building': 'Some Building'
                }
            }
        }
    }

    transport_interface = DummyTransportInterface('')
    smap = SmapInterface(transport_interface)

    loop.run_until_complete(
        smap.post_data(series, uuid, source_name, path, metadata)
    )

    assert json.loads(transport_interface.received_post_data) == expected_data


def test_post_readings() -> None:
    loop = asyncio.get_event_loop()

    uuid = UUID('12345678-1234-5678-9abc-123456789abc')
    series = pd.Series(
        [5.0, 8.0, 12.0, -5.3],
        index=pd.to_datetime(
            [
                datetime(2017, 1, 1, tzinfo=timezone.utc),
                datetime(2017, 2, 1, tzinfo=timezone.utc),
                datetime(2017, 3, 1, tzinfo=timezone.utc),
                datetime(2017, 4, 1, tzinfo=timezone.utc),
            ],
            utc=True
        ),
        name=str(uuid)
    )
    path = '/some/path'

    transport_result = [
        {
            "Path": path,
            "uuid": str(uuid)
        }
    ]

    expected_query = "select Path where uuid = '{}'".format(uuid)

    expected_data = {
        path: {
            'uuid': str(uuid),
            'Readings': [
                [1483228800000, 5.0],
                [1485907200000, 8.0],
                [1488326400000, 12.0],
                [1491004800000, -5.3]
            ]
        }
    }

    transport_interface = DummyTransportInterface(json.dumps(transport_result))
    smap = SmapInterface(transport_interface)

    loop.run_until_complete(
        smap.post_readings((uuid, series))
    )

    assert transport_interface.received_fetch_query == expected_query
    assert json.loads(transport_interface.received_post_data) == expected_data
