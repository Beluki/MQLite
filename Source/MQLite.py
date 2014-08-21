#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLite.
Pattern match JSON like you query Freebase, using a simple MQL dialect.
"""


import json
import os
import sys

from collections import OrderedDict
from json import JSONDecoder


# API:

# Matchers:

# Matchers are classes that the compiler emits to test input data.
# Each matcher implements a "match" method that returns the data
# or NoMatch depending on whether the test succeeded or not.

class _NoMatch(object):
    """
    A custom class to represent no matches.
    Needed because None is a legitimate match.
    """
    pass

NoMatch = _NoMatch()


# Simple matchers:

class MatchAny(object):
    """
    Match any input data.
    """
    def match(self, data):
        return data


class MatchEqual(object):
    """
    Match data equal to a given value.
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        if self.value == data:
            return data
        else:
            return NoMatch


# Empty collections:
# (those are just an optimization to avoid loops in the common case)

class MatchEmptyDict(object):
    """
    Match an empty dictionary.
    """
    def match(self, data):
        if data == {}:
            return data
        else:
            return NoMatch


class MatchEmptyList(object):
    """
    Match an empty list.
    """
    def match(self, data):
        if data == []:
            return data
        else:
            return NoMatch


# Populated collections:

class MatchDict(object):
    """
    Perform matches between a compiled dict
    (where all values are matching classes) and input data.

    The match succeeds if:
        - The input data is a dict.
        - All keys in the input dict are present in the input data.
        - All values for those keys match.

    The result is a dict containing all the matching keys/values.
    """
    def __init__(self, compiled_dict):
        self.items = list(compiled_dict.items())

    def match(self, data):

        # not a dict?
        if not isinstance(data, dict):
            return NoMatch

        result = {}
        for key, matcher in self.items:

            # key present?
            if not key in data:
                return NoMatch

            current = matcher.match(data[key])

            # value matches?
            if current is NoMatch:
                return NoMatch

            result[key] = current

        return result


class MatchList(object):
    """
    Perform matches between a compiled list
    (where all values are matching classes) and input data.

    The match suceeds if:
        - The input data is a list.
        - Each value matches at least one element in the input data.

    The result is a list containing all the matches.
    """
    def __init__(self, compiled_list):
        self.compiled_list = compiled_list

    def match(self, data):

        # not a list?
        if not isinstance(data, list):
            return NoMatch

        result = []
        for matcher in self.compiled_list:
            matched = False

            for value in data:
                current = matcher.match(value)

                if not current is NoMatch:
                    matched = True
                    result.append(current)

            # at least one match?
            if not matched:
                return NoMatch

        return result


# Wrappers:

class MatchToLists(object):
    """
    Wrap a matcher so that it can be mapped over a list.
    The match succeeds if at least one of the list elements matches.
    """
    def __init__(self, matcher):
        self.matcher = matcher

    def match(self, data):

        # list?
        if isinstance(data, list):
            result = []

            for value in data:
                current = self.matcher.match(value)

                if not current is NoMatch:
                    result.append(current)

            # at least one match?
            if len(result) == 0:
                return NoMatch

            return result

        # fall back to the matcher behaviour:
        return self.matcher.match(data)


# Compiler from JSON to matchers:

class CompilerException(Exception):
    pass


class Compiler(object):

    def __init__(self):
        pass

    def compile(self, pattern):
        """
        Compile a pattern to a matching class.
        """

        # repetitive but allows compiler subclasses
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

        raise CompilerException('Unknown type: %s' % pattern)

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
        or MatchDict instances that allow lists as targets.
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
        or MatchList instances.
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

        return self._pattern_compiled.match(data)


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


# IO utils and formatting JSON:
# (part of the API because the shell will use them too)

NEWLINES = {
    'dos'    : '\r\n',
    'mac'    : '\r',
    'unix'   : '\n',
    'system' : os.linesep,
}


def binary_stdin_read_utf8():
    """ Read from stdin as UTF-8 (allowing an optional BOM). """
    content = sys.stdin.buffer.read()
    return content.decode('utf-8-sig')


def binary_stdout_write_utf8(text):
    """ Write 'text' to stdout as UTF-8. """
    sys.stdout.buffer.write(text.encode('utf-8'))


class JSONFormatter(object):
    """
    A helper to print JSON to stdout in a desired format.
    It's just a wrapper over json.dumps() with configurable newlines.
    """
    def __init__(self, ensure_ascii, indent, sort_keys, newline):
        self.ensure_ascii = ensure_ascii
        self.indent = indent
        self.sort_keys = sort_keys
        self.newline = newline

    def dump(self, jsondata):
        """
        Serialize jsondata to a JSON formatted string
        using the formatter settings.
        """
        text = json.dumps(jsondata, ensure_ascii = self.ensure_ascii,
            indent = self.indent, sort_keys = self.sort_keys)

        # if not indenting, there are no newlines:
        if self.indent is None:
            return text

        # JSON strings can't contain control characters, so this is safe.
        # (U+2028 line separator and U+2029 paragraph separator are allowed)
        else:

            # json.dumps() always uses '\n' for newlines, but let's do
            # a sanity check just in case the implementation changes:
            if '\r' in text:
                raise ValueError('Internal error: CR from json.dumps()')

            return text.replace('\n', self.newline)

    def stdout(self, jsondata):
        """
        Serialize jsondata and print the result to stdout.
        """
        binary_stdout_write_utf8(self.dump(jsondata))


# Program (e.g. python -m MQLite ...)

from argparse import ArgumentParser, RawDescriptionHelpFormatter


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using the platform encoding and newline format. """
    print(line)


def errln(line):
    """ Write 'line' to stderr, using the platform encoding and newline format. """
    print(line, file = sys.stderr)


# Parser:

def make_parser():
    parser = ArgumentParser(
        description = __doc__,
        formatter_class = RawDescriptionHelpFormatter,
        usage  = 'MQLite.py pattern [option [options ...]]')

    # required:
    parser.add_argument('pattern',
        help = 'JSON pattern to match against stdin',
        metavar = 'pattern')

    # optional:
    parser.add_argument('--strict',
        help = 'exit with an error message and status 1 when no match',
        action = 'store_true')

    # optional, output format:
    output_format = parser.add_argument_group('output format')

    output_format.add_argument('--ascii',
        help = 'escape non-ascii characters',
        action = 'store_true')

    output_format.add_argument('--indent',
        help = 'use N spaces of indentation (-1 to disable)',
        metavar = 'N',
        type = int,
        default = 4)

    output_format.add_argument('--sort-keys',
        help = 'sort dictionaries by key before printing',
        action = 'store_true')

    output_format.add_argument('--newline',
        help = 'use a specific newline mode (default: system)',
        choices = ['dos', 'mac', 'unix', 'system'],
        default = 'system')

    return parser


# Entry point:

def main():
    parser = make_parser()
    options = parser.parse_args()

    newline = NEWLINES[options.newline]
    indent = options.indent

    if options.indent < 0:
        indent = None

    try:
        data = binary_stdin_read_utf8()
        datajson = json.loads(data)

        result = JSONPattern(options.pattern).match(datajson)

        if result is NoMatch:
            if options.strict:
                errln('error: no match')
                sys.exit(1)
        else:
            formatter = JSONFormatter(options.ascii, indent, options.sort_keys, newline)
            formatter.stdout(result)

    except Exception as err:
        errln(str(err))
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

