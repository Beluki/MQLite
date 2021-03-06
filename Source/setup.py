# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name = 'MQLite',
    version = '2016.02.02',
    url = 'https://github.com/Beluki/MQLite',
    license = 'See Documentation/License',
    author = 'Beluki',
    author_email = 'beluki@gmx.com',
    description = 'Pattern match JSON like you query Freebase, using a simple MQL dialect.',
    py_modules = ['MQLite'],
    scripts = ['MQLite.py', 'MQLiteSH.py'],
    zip_safe = False,
    platforms = 'any',
    classifiers = [
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Code Generators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ]
)

