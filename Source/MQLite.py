#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLite.
Pattern match JSON like you query Freebase, using a simple MQL dialect.
"""


import json
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using UTF-8 and platform newline. """
    print(line)


def errln(line):
    """ Write 'line' to stderr, using UTF-8 and platform newline. """
    print(line, file = sys.stderr)


# Entry point:

def main():
    pass


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

