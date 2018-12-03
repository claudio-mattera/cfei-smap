from uuid import UUID
from datetime import datetime, timezone

import pandas as pd
from pandas.util.testing import assert_series_equal

import cfei.smap


def test_parse_readings() -> None:
    uuid = UUID('12345678-1234-1234-1234-123456789abc')
    readings = [
        [1484006400000, 12],
        [1491004800000, -34],
        [1491523200000, 53]
    ]

    expected = pd.Series(
        [12, -34, 53],
        index=pd.to_datetime([
                1484006400000,
                1491004800000,
                1491523200000,
            ],
            unit='ms',
            utc=True
        ),
        name=str(uuid)
    )

    actual = cfei.smap._parse_readings(uuid, readings)

    assert_series_equal(actual, expected)


def test_to_milli_timestamp() -> None:
    expected = 1491004800000
    actual = cfei.smap._to_milli_timestamp(datetime(2017, 4, 1, tzinfo=timezone.utc))

    assert expected == actual


def test_intertwine_series() -> None:
    a = pd.Series([1, 2, 3, 4], index=[1, 3, 4, 9])
    b = pd.Series([5, 6, 7, 8], index=[2, 3, 8, 9])

    expected = pd.Series([1, 5, 2, 3, 7, 4], index=[1, 2, 3, 4, 8, 9])

    actual = cfei.smap.intertwine_series([a, b])

    assert_series_equal(actual, expected)


def test_make_update_payload() -> None:
    uuid = UUID('12345678-1234-1234-1234-123456789abc')

    readings = pd.Series(
        [12, -34, 53],
        index=pd.to_datetime([
                1484006400000,
                1491004800000,
                1491523200000,
            ],
            unit='ms',
            utc=True
        ),
        name=str(uuid)
    )

    metadata = {
        'SourceName': 'Some Source Name'
    }

    expected = {
        'uuid': str(uuid),
        'Readings': [
            [1484006400000, 12],
            [1491004800000, -34],
            [1491523200000, 53]
        ],
        'Metadata': {
            'SourceName': 'Some Source Name'
        }
    }

    actual = cfei.smap._make_update_payload(
        uuid,
        readings,
        metadata,
        properties=None,
    )

    assert expected == actual


def test_generate_uuid_as_in_java() -> None:
    source_name = 'My Source Name'
    path = '/path/to/time-series'

    expected = UUID('c5d98d49-8af6-37e1-9248-9285be1ae8dd')

    actual = cfei.smap.generate_uuid_as_in_java(source_name, path)

    assert expected == actual
