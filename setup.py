#!/usr/bin/env python

import sys

from setuptools import setup

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
pytest_runner = ['pytest-runner'] if needs_pytest else []

setup(
    name='cfei-smap',
    version='1.2.0',
    description='Interface to sMAP',
    long_description=open('Readme.md').read(),
    author='Claudio Giovanni Mattera',
    author_email='cgim@mmmi.sdu.dk',
    url='https://github.com/sdu-cfei/cfei-smap/',
    license='MIT',
    packages=[
        'cfei.smap',
        'cfei.smap.transport',
    ],
    include_package_data=True,
    scripts=[
        'scripts/smap',
    ],
    install_requires=[
        'pandas',
        'typing',
        'aiohttp',
        'appdirs',
        'jsonschema',
        'iso8601',
    ],
    setup_requires=pytest_runner,
    tests_require=['pytest'],
)
