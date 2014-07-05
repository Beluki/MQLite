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


# Matchers.

class NoMatch(object):
    """
    A custom class to represent no matches.
    Needed because None is a legitimate match.
    """
    pass


_no_match = NoMatch()


class MatchAny(object):
    """
    Matches any input data.
    """
    def __call__(self, data):
        return data

class MatchEqual(object):
    """
    Matches input data that is equal to a given value.
    """
    def __init__(self, value):
        self.value = value

    def __call__(self, data):
        if self.value == data:
            return data
        else:
            return _no_match


# Compiler from JSON to matchers (callables).

class CompilerException(Exception):
    pass


class Compiler(object):

    def __init__(self):
        pass

    def compile(self, pattern):
        """
        Compile a pattern to a matching class.
        """
        if pattern is None:
            return MatchAny()

        if type(pattern) in [bool, int, float]:
            return MatchEqual(pattern)

        raise CompilerException('Unknown datatype: %s' % pattern)


# Entry point:

def main():
    compiler = Compiler()

    match = compiler.compile(True)
    data = True

    print(match(data))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

