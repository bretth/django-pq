#!/usr/bin/env python

# Fix for Python issue 15881, fixed in 2.7.6 and 3.2
try:
    import multiprocessing
except ImportError:
    pass

try:
    from setuptools import setup
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

setup(
    setup_requires=['d2to1'],
    d2to1=True
)
