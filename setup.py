#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_packages
from fuct import __version__

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name="fuct",
    version=__version__,
    packages=find_packages(),
    install_requires=[
        'pyserial >= 2.7',
        'colorlog >= 2.0.0'
    ],
    entry_points={
        'console_scripts': ['fuct = fuct.main:main']
    },
    author="Ari Karhu",
    author_email='ari@baboonplanet.com',
    description='FUCT - FreeEMS Unified Console Tool',
    long_description=readme + '\n\n' + history,
    license='BSD',
    url='https://github.com/MrOnion/fuct',
    platforms=['any'],
    keywords='freeems loader command line ',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7'
    ]
)
