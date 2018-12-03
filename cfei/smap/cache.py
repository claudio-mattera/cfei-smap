from datetime import datetime
import logging
import pickle
from uuid import UUID
from os.path import join
from os import makedirs
from hashlib import sha512
from base64 import b32encode

import pandas as pd
import typing

import appdirs


def load_readings_from_cache(
            start: datetime,
            end: datetime,
            where: typing.Text,
            limit: int,
            streamlimit: int,
        ) -> typing.Dict[UUID, pd.Series]:
    """
    Load readings from local cache

    Cache file name is generated from the where clause. If such file exists,
    it is loaded using `pickle` library. Loading fails if:

    - Data contained in cache does not cover the entire period [start, end];
    - Data contained in cache had different `limit` or `streamlimit` arguments.

    :param start: Query start time.
    :type start: datetime
    :param end: Query end time.
    :type end: datetime
    :param where: Query `WHERE` condition.
    :type where: str
    :param limit: Maximum number of readings
    :type limit: int
    :param streamlimit: Maximum number of streams
    :type streamlimit: int

    :returns: A mapping UUID -> values.
    :rtype: dict(UUID, pd.Series)

    :raises RuntimeError: If cache loading failed.
    """

    logger = logging.getLogger(__name__)
    cache_file_path = _get_cache_file_path(where)
    logger.debug("Loading data from cache file: %s", cache_file_path)
    with open(cache_file_path, 'rb') as cache_file:
        entry = pickle.load(cache_file)  # typing.Dict[typing.Text, typing.Any]
    if entry['start'] > start:
        raise RuntimeError('cache starts too late')
    if entry['end'] < end:
        raise RuntimeError('cache ends too early')
    if entry['limit'] != limit:
        raise RuntimeError('cache limit mismatch')
    if entry['streamlimit'] != streamlimit:
        raise RuntimeError('cache stream limit mismatch')
    data = entry['data']  # type: typing.Dict[UUID, typing.Any]
    return data


def save_readings_to_cache(
            data: typing.Dict[UUID, typing.Any],
            start: datetime,
            end: datetime,
            where: typing.Text,
            limit: int,
            streamlimit: int,
        ) -> None:
    """
    Save readings to local cache

    Cache file name is generated from the where clause.

    :param data: Readings.
    :type data: dict(UUID, typing.Any)
    :param start: Query start time.
    :type start: datetime
    :param end: Query end time.
    :type end: datetime
    :param where: Query `WHERE` condition.
    :type where: str
    :param limit: Maximum number of readings
    :type limit: int
    :param streamlimit: Maximum number of streams
    :type streamlimit: int
    """

    logger = logging.getLogger(__name__)

    entry = {
        'start': start,
        'end': end,
        'data': data,
        'limit': limit,
        'streamlimit': streamlimit,
    }
    try:
        cache_file_path = _get_cache_file_path(where)
        logger.debug('Saving to cache')
        cache_dir = _get_cache_dir()
        makedirs(cache_dir, exist_ok=True)
        with open(cache_file_path, 'wb') as cache_file:
            pickle.dump(entry, cache_file)
    except Exception as other_exception:
        logger.warning(
            "Could not save cache: %s",
            str(other_exception)
        )


def load_raw_from_cache(
            query: typing.Text,
        ) -> typing.Text:
    """
    Load raw content from local cache

    Cache file name is generated from the entire query. If such file exists,
    it is loaded using `pickle` library.

    :param query: Query.
    :type query: str

    :returns: Raw data.
    :rtype: str

    :raises RuntimeError: If cache loading failed.
    """

    logger = logging.getLogger(__name__)

    cache_file_path = _get_cache_file_path(query)
    logger.debug("Loading data from cache file: %s", cache_file_path)
    with open(cache_file_path, 'rb') as cache_file:
        data = pickle.load(cache_file)  # type: typing.Text
    return data


def save_raw_to_cache(
            data: typing.Text,
            query: typing.Text,
        ) -> None:
    """
    Save raw data to local cache

    Cache file name is generated from the entire query.

    :param data: Raw data.
    :type data: str
    :param query: Query.
    :type query: str
    """

    logger = logging.getLogger(__name__)

    try:
        cache_file_path = _get_cache_file_path(query)
        logger.debug('Saving to cache')
        cache_dir = _get_cache_dir()
        makedirs(cache_dir, exist_ok=True)
        with open(cache_file_path, 'wb') as cache_file:
            pickle.dump(data, cache_file)
    except Exception as other_exception:
        logger.warning(
            "Could not save cache: %s",
            str(other_exception)
        )


def _get_cache_dir() -> typing.Text:
    cache_dir = appdirs.user_cache_dir(
        appname='sMAP-Python',
        appauthor='dk.sdu.mmmi.cfei',
    )  # type: typing.Text
    return cache_dir


def _get_cache_file_path(text: typing.Text) -> typing.Text:
    cache_dir = _get_cache_dir()

    # Leave UTF-8 here, do not use configurable encoding.
    # This is used to generate the cache file name.
    hash_bytes = sha512(text.encode('utf-8')).digest()
    cache_file_name = b32encode(hash_bytes).decode('utf-8')

    cache_file_path = join(cache_dir, cache_file_name)  # type: typing.Text
    return cache_file_path
