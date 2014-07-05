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

class MatchMulti(object):

    def __init__(self, matcher):
        self.matcher = matcher

    def __call__(self, data):
        if isinstance(data, list):
            result = []

            for value in data:
                current = self.matcher(value)

                if not current is _no_match:
                    result.append(current)

            if len(result) == 0:
                return _no_match

            return result

        else:
            return self.matcher(data)

class MatchEmptyDict(object):
    """
    Matches an empty dictionary.
    """
    def __call__(self, data):
        if data == {}:
            return data
        else:
            return _no_match


class MatchEmptyList(object):
    """
    Matches an empty list.
    """
    def __call__(self, data):
        if data == []:
            return data
        else:
            return _no_match


class MatchDict(object):
    """
    Performs matches between a compiled dict (where all values are
    matching classes) and input data.

    The match succeeds if:
        - The input data is a dict.
        - All keys in the input dict are present in the input data.
        - All values for those keys match.

    The result is a dict containing all the matching keys/values.
    """
    def __init__(self, compiled_dict):
        self.compiled_dict = compiled_dict

    def __call__(self, data):

        # not a dict?
        if not isinstance(data, dict):
            return _no_match

        result = {}
        for key, matcher in self.compiled_dict.items():

            # key in compiled dict not in data?
            if not key in data:
                return _no_match

            # try to match values:
            current = matcher(data[key])
            if current is _no_match:
                return _no_match

            result[key] = current

        return result


class MatchList(object):
    """
    Performs matches between a compiled list (where all values are
    matching classes) and input data.

    Each value in the compiled list is considered a pattern
    and is matched against each value in the data list.

    The match suceeds if:
        - The input data is a list.
        - Each pattern matches at least one element in the input data.

    The result is a list containing all the matches.
    """
    def __init__(self, compiled_list):
        self.list = compiled_list

    def __call__(self, data):

        # not a list?
        if not isinstance(data, list):
            return _no_match

        result = []
        for matcher in self.list:
            matched = False

            for value in data:
                current = matcher(value)

                if not current is _no_match:
                    matched = True
                    result.append(current)

            # at least one match is required:
            if not matched:
                return _no_match

        return result


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
            return self.compile_none(pattern)

        if type(pattern) in [bool, int, float, str]:
            return MatchMulti(self.compile_literal(pattern))

        if isinstance(pattern, dict):
            return MatchMulti(self.compile_dict(pattern))

        if isinstance(pattern, list):
            return self.compile_list(pattern)

        raise CompilerException('Unknown datatype: %s' % pattern)

    def compile_none(self, pattern):
        """
        None matches anything.
        """
        return MatchAny()

    def compile_literal(self, pattern):
        """
        Literals match themselves.
        """
        return MatchEqual(pattern)

    def compile_dict(self, pattern):
        """
        Dicts are compiled into either MatchEmptyDict
        or MatchDict classes.
        """
        if pattern == {}:
            return MatchEmptyDict()

        compiled_dict = {}

        for key, value in pattern.items():
            compiled_dict[key] = self.compile(value)

        return MatchDict(compiled_dict)

    def compile_list(self, pattern):
        """
        Lists are compiled into either MatchEmptyList
        or MatchList classes.
        """
        if pattern == []:
            return MatchEmptyList()

        compiled_list = [self.compile(value) for value in pattern]
        return MatchList(compiled_list)


# Entry point:

def main():
    compiler = Compiler()

    data = [1, 2, 1]
    pattern = None

    match = compiler.compile(pattern)

    print(match(data))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
