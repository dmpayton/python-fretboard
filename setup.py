#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

with open('./requirements.txt') as fd:
    requirements = fd.read().splitlines()

__version__ = '1.0.0'

setup(
    name='fretboard',
    version=__version__,
    license='MIT',

    author='Derek Payton',
    author_email='derek.payton@gmail.com',

    description='Fretboard is a python library for generating SVG fretboard images and chord charts in Python.',
    long_description=open('README.rst').read(),

    url='https://github.com/dmpayton/python-fretboard',
    download_url='https://github.com/dmpayton/python-fretboard/tarball/v%s' % __version__,

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
    keywords='guitar fretboard chord',

    packages=['fretboard'],
    install_requires=requirements,
)
