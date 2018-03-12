#!/usr/bin/env/python
from setuptools import setup

setup(
    name='gemini_wrapper',
    version='0.1',
    description='Description.',
    author='Jared Burke',
    packages=['src'],
    entry_points={
        'console_scripts': ['gemini_wrapper = src.main:main']
    },
    url='')

