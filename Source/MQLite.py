#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLite.
Pattern match JSON like you query Freebase, using a simple MQL dialect.
"""


import json
import sys

from collections import OrderedDict
from json import JSONDecoder

from argparse import ArgumentParser, RawDescriptionHelpFormatter


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using UTF-8 and platform newline. """
    print(line)


def errln(line):
    """ Write 'line' to stderr, using UTF-8 and platform newline. """
    print(line, file = sys.stderr)


# Utils:

def load_json(filepath):
    """
    Open filepath as UTF-8 and try to parse the content as JSON.
    """
    with open(filepath, encoding = 'utf-8') as descriptor:
        return json.load(descriptor)


# Matcher classes:

# Matchers are callables that the compiler emits while walking JSON nodes.
# Each matcher tests for particular data or combines other matchers.

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
    Matches data equal to a given value.
    """
    def __init__(self, value):
        self.value = value

    def __call__(self, data):
        if data == self.value:
            return data
        else:
            return _no_match


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
    Performs matches between a compiled dict
    (where all values are matching classes) and input data.

    The match succeeds if:
        - The input data is a dict.
        - All keys in the input dict are present in the input data.
        - All values for those keys match.

    The result is a dict containing all the matching keys/values.
    """
    def __init__(self, compiled_dict):
        self.items = list(compiled_dict.items())

    def __call__(self, data):

        # not a dict?
        if not isinstance(data, dict):
            return _no_match

        result = {}
        for key, matcher in self.items:

            # key present?
            if not key in data:
                return _no_match

            # value matches?
            current = matcher(data[key])
            if current is _no_match:
                return _no_match

            result[key] = current

        return result


class MatchList(object):
    """
    Performs matches between a compiled list
    (where all values are matching classes) and input data.

    Each value in the compiled list is considered a pattern
    and is matched against each value in the data list.

    The match suceeds if:
        - The input data is a list.
        - Each pattern matches at least one element in the input data.

    The result is a list containing all the matches.
    """
    def __init__(self, compiled_list):
        self.compiled_list = compiled_list

    def __call__(self, data):

        # not a list?
        if not isinstance(data, list):
            return _no_match

        result = []
        for matcher in self.compiled_list:
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


class MatchToLists(object):
    """
    Wraps a matching class so that when used against a list
    it tries to match every element and return the matching results.
    The match succeeds if any of the list elements matches.
    """
    def __init__(self, matcher):
        self.matcher = matcher

    def __call__(self, data):

        # list?:
        if isinstance(data, list):
            result = []

            for value in data:
                current = self.matcher(value)

                if not current is _no_match:
                    result.append(current)

            if len(result) > 0:
                return result

            return _no_match

        # fallback to the matcher behaviour otherwise:
        return self.matcher(data)


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

        # this is fairly repetitive but allows compiler subclasses
        # to override compiling behaviour for a single type:

        if pattern is None:
            return self.compile_none(pattern)

        if isinstance(pattern, bool):
            return self.compile_bool(pattern)

        if isinstance(pattern, int):
            return self.compile_int(pattern)

        if isinstance(pattern, float):
            return self.compile_float(pattern)

        if isinstance(pattern, str):
            return self.compile_str(pattern)

        if isinstance(pattern, dict):
            return self.compile_dict(pattern)

        if isinstance(pattern, list):
            return self.compile_list(pattern)

        raise CompilerException('Unknown datatype: %s' % pattern)

    def compile_none(self, pattern):
        """
        None matches anything.
        """
        return MatchAny()

    def compile_bool(self, pattern):
        """
        Booleans match themselves and allow lists as targets.
        """
        return MatchToLists(MatchEqual(pattern))

    def compile_int(self, pattern):
        """
        Integers match themselves and allow lists as targets.
        """
        return MatchToLists(MatchEqual(pattern))

    def compile_float(self, pattern):
        """
        Floats match themselves and allow lists as targets.
        """
        return MatchToLists(MatchEqual(pattern))

    def compile_str(self, pattern):
        """
        Strings match themselves and allow lists as targets.
        """
        return MatchToLists(MatchEqual(pattern))

    def compile_dict(self, pattern):
        """
        Dicts are compiled into either MatchEmptyDict
        or MatchDict classes that allow lists as targets.
        """
        if pattern == {}:
            return MatchToLists(MatchEmptyDict())

        compiled_dict = OrderedDict()

        for key, value in pattern.items():
            compiled_dict[key] = self.compile(value)

        return MatchToLists(MatchDict(compiled_dict))

    def compile_list(self, pattern):
        """
        Lists are compiled into either MatchEmptyList
        or MatchList classes.
        """
        if pattern == []:
            return MatchEmptyList()

        compiled_list = [self.compile(value) for value in pattern]
        return MatchList(compiled_list)


# Higher-level pattern classes:

class Pattern(object):
    """
    A raw (Python object) pattern.
    """
    def __init__(self, data):
        self._compiler = Compiler()
        self._data = data
        self._pattern_compiled = None

    def compile(self):
        """
        Compile this pattern.
        """
        self._pattern_compiled = self._compiler.compile(self._data)

    def match(self, data):
        """
        Execute this pattern against the given data.
        """
        if self._pattern_compiled is None:
            self.compile()

        return self._pattern_compiled(data)


class JSONPattern(object):
    """
    A JSON pattern.
    """
    def __init__(self, jsondata):
        self._decoder = JSONDecoder(object_pairs_hook = OrderedDict)
        self._jsondata = jsondata
        self._pattern_decoded = None

    def decode(self):
        """
        Decode the JSON.
        """
        self._pattern_decoded = Pattern(self._decoder.decode(self._jsondata))

    def match(self, data):
        """
        Execute this pattern against the given data.
        """
        if self._pattern_decoded is None:
            self.decode()

        return self._pattern_decoded.match(data)


# A simple read-eval-print-loop:

class REPL(object):

    def __init__(self, data, indent = 4, sort_keys = False):
        self.data = data
        self.prompt = '>>> '
        self.indent = indent
        self.sort_keys = sort_keys

    def _read_eval_print(self):
        """
        Parse, execute and print the result of a given pattern.
        """
        text = input(self.prompt)

        if text:
            result = JSONPattern(text).match(self.data)

            if not result is _no_match:
                outln(json.dumps(result, indent = self.indent, sort_keys = self.sort_keys))

    def run(self):
        """
        Start the read-eval-print-loop.
        """
        while True:
            try:
                self._read_eval_print()

            except EOFError:
                break

            except KeyboardInterrupt:
                errln('')
                errln('KeyboardInterrupt')

            except Exception as err:
                errln('Error: ' + str(err))


# Parser:

def make_parser():
    parser = ArgumentParser(
        description = __doc__,
        formatter_class = RawDescriptionHelpFormatter,
        epilog = 'example: MQLite.py [file.json]',
        usage  = 'MQLite.py [filepath]')

    # optional:
    parser.add_argument('filepath',
        help = 'run a repl with filepath as the JSON data',
        metavar = 'filepath')

    return parser


# Entry point:

def main():
    parser = make_parser()
    options = parser.parse_args()

    data = None

    try:
        data = load_json(options.filepath)

    except Exception as err:
        errln(str(err))
        sys.exit(1)

    repl = REPL(data)
    repl.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

