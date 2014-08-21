#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLiteSH.
An interactive shell for MQLite.
"""


import json
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using the platform encoding and newline format. """
    print(line)


def errln(line):
    """ Write 'line' to stderr, using the platform encoding and newline format. """
    print(line, file = sys.stderr)


# Non-builtin imports:

try:
    from MQLite import JSONPattern, NoMatch

except ImportError:
    errln('MQLiteSH requires the following modules:')
    errln('MQLite 2014.08.19+ - <https://github.com/Beluki/MQLite>')
    sys.exit(1)


# Parser:

def make_parser():
    parser = ArgumentParser(
        description = __doc__,
        formatter_class = RawDescriptionHelpFormatter,
        usage  = 'MQLiteSH.py filepath [option [options ...]]')

    # required:
    parser.add_argument('filepath',
        help = 'JSON file to use as input data on the REPL',
        metavar = 'filepath')

    return parser


# Entry point:

def main():
    parser = make_parser()
    options = parser.parse_args()

    pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

