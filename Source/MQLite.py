#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLite.
Pattern match JSON like you query Freebase, using a simple MQL dialect.
"""


import json
import os
import re
import sys

from collections import OrderedDict
from json import JSONDecoder


# Nodes:
# The MQLite compiler emits various kinds of nodes.
# All of them implement a "match" method that tests data
# or combines other nodes to do so.


# Matchers:
# Nodes that return the data or NoMatch depending on a test.
# Used to implement the basic pattern matching behavior.

class _NoMatch(object):
    """
    A custom class to represent no matches.
    Needed because None is a legitimate match.
    """
    pass

NoMatch = _NoMatch()


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


class MatchDict(object):
    """
    Perform matches between a matchers and a constraints dict
    and input data.

    The match succeeds if:
        - The input data is a dict.
        - All the constraints match.
        - All the matchers match.

    The result is a dict containing all the matching keys/values.
    """
    def __init__(self, matchers, constraints, directives, optional_keys, include_all_keys):
        self.matchers = list(matchers.items())
        self.constraints = list(constraints.items())
        self.directives = directives
        self.optional_keys = optional_keys
        self.include_all_keys = include_all_keys

    def match(self, data):

        # not a dict?
        if not isinstance(data, dict):
            return NoMatch

        # constraints match?
        for key, constraint in self.constraints:
            if not key in data or not constraint.match(data[key]):
                return NoMatch

        # matchers match?
        result = {}
        for key, matcher in self.matchers:
            if not key in data:
                return NoMatch

            current = matcher.match(data[key])

            if current is NoMatch:
                if key in self.optional_keys:
                    result[key] = None
                else:
                    return NoMatch
            else:
                result[key] = current

        # add all the data keys to the result if needed:
        if self.include_all_keys:
            for key, value in data.items():
                if not key in result:
                    result[key] = value

        return result


class MatchList(object):
    """
    Perform matches between a matchers list and input data.

    The match suceeds if:
        - The input data is a list.
        - Each matcher matches at least one element in the input data.

    The result is a list containing all the matches.
    """
    def __init__(self, matchers):
        self.matchers = matchers

    def match(self, data):

        # not a list?
        if not isinstance(data, list):
            return NoMatch

        result = []
        for matcher in self.matchers:

            # collect results for the current matcher:
            matcher_results = []
            for value in data:
                current = matcher.match(value)

                if current is not NoMatch:
                    matcher_results.append(current)

            # at least one match?
            if len(matcher_results) == 0:
                return NoMatch

            # apply directives for dictionaries:
            if isinstance(matcher, MatchDict):
                for directive in matcher.directives:
                    matcher_results = directive.match(matcher_results)

            result += matcher_results

        return result


# Constraints:
# Nodes that test a property of the data and return True or False.
# Used to implement operators such as >, <, ...

class ConstraintMoreThan(object):
    """
    Tests that the data is bigger than a particular value.
    (operator > in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return data > self.value


class ConstraintMoreOrEqualTo(object):
    """
    Tests that the data is bigger or equal to a particular value.
    (operator >= in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return data >= self.value


class ConstraintLessThan(object):
    """
    Tests that the data is smaller than a particular value.
    (operator < in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return data < self.value


class ConstraintLessOrEqualTo(object):
    """
    Tests that the data is smaller or equal to a particular value.
    (operator <= in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return data <= self.value


class ConstraintEqualTo(object):
    """
    Tests that the data is equal to a particular value.
    (operator == in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return data == self.value


class ConstraintNotEqualTo(object):
    """
    Tests that the data is not equal to a particular value.
    (operator != in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return data != self.value


class ConstraintRegex(object):
    """
    Tests that the data matches a regular expression.
    (operator "regex" in MQLite)
    """
    def __init__(self, regex):
        self.regex = regex

    def match(self, data):
        return re.match(self.regex, data) is not None


class ConstraintNotRegex(object):
    """
    Tests that the data does NOT match a regular expression.
    (operator "!regex" in MQLite)
    """
    def __init__(self, regex):
        self.regex = regex

    def match(self, data):
        return re.match(self.regex, data) is None


class ConstraintIn(object):
    """
    Tests that the data is equal to at least one element of a list of values.
    (operator "in" in MQLite)
    """
    def __init__(self, values):
        self.values = values

    def match(self, data):
        return data in self.values


class ConstraintNotIn(object):
    """
    Tests that the data is not equal to any of a list of values.
    (operator "!in" in MQLite)
    """
    def __init__(self, values):
        self.values = values

    def match(self, data):
        return data not in self.values


class ConstraintContain(object):
    """
    Tests that the data contains one value.
    (operator "contain" in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return self.value in data


class ConstraintNotContain(object):
    """
    Tests that the data does NOT contain a value.
    (operator "!contain" in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return self.value not in data


# Directives:
# Nodes that transform the data into something else.

class DirectiveLimit(object):
    """
    Take at most N elements from data.
    """
    def __init__(self, limit):
        self.limit = limit

    def match(self, data):
        return data[0: self.limit]


class DirectiveSortByKey(object):
    """
    Sort dictionaries by a given key.
    """
    def __init__(self, key):
        if len(key) > 1 and key.startswith('-'):
            self.reverse = True
            self.key = key[1:]
        else:
            self.reverse = False
            self.key = key

    def match(self, data):
        return sorted(data, key = lambda value: value[self.key], reverse = self.reverse)


# Wrappers:
# Take nodes as arguments and modify/combine their behaviour.

class WrapConstraintsAnd(object):
    """
    Combine two constraints into a single one
    returning True/False depending on whether both match.
    """
    def __init__(self, constraint_a, constraint_b):
        self.constraint_a = constraint_a
        self.constraint_b = constraint_b

    def match(self, data):
        return self.constraint_a.match(data) and self.constraint_b.match(data)


# Compiler:

class CompilerException(Exception):
    pass


class Compiler(object):
    """
    The MQLite compiler.
    """
    constraints = {
        '>'        :  ConstraintMoreThan,
        '>='       :  ConstraintMoreOrEqualTo,
        '<'        :  ConstraintLessThan,
        '<='       :  ConstraintLessOrEqualTo,
        '=='       :  ConstraintEqualTo,
        '!='       :  ConstraintNotEqualTo,
        'regex'    :  ConstraintRegex,
        '!regex'   :  ConstraintNotRegex,
        'in'       :  ConstraintIn,
        '!in'      :  ConstraintNotIn,
        'contain'  :  ConstraintContain,
        '!contain' :  ConstraintNotContain,
    }

    directives = {
        '__limit__' : DirectiveLimit,
        '__sort__'  : DirectiveSortByKey,
    }

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

        raise CompilerException('Unknown type: {}'.format(pattern))

    def compile_none(self, pattern):
        """
        None matches anything.
        """
        return MatchAny()

    def compile_bool(self, pattern):
        """
        Booleans match themselves.
        """
        return MatchEqual(pattern)

    def compile_int(self, pattern):
        """
        Integers match themselves.
        """
        return MatchEqual(pattern)

    def compile_float(self, pattern):
        """
        Floats match themselves.
        """
        return MatchEqual(pattern)

    def compile_str(self, pattern):
        """
        Strings match themselves.
        """
        return MatchEqual(pattern)

    def compile_dict(self, pattern):
        """
        Dicts are compiled into either MatchEmptyDict or MatchDict instances.
        """
        # optimize empty patterns:
        if pattern == {}:
            return MatchEmptyDict()

        matchers = OrderedDict()
        constraints = OrderedDict()
        directives = []

        optional_keys = set()
        include_all_keys = False

        for key, value in pattern.items():

            # directive?
            is_directive = False
            if key in self.directives:
                directive = self.directives[key](value)
                directives.append(directive)
                is_directive = True

            # constraint?
            is_constraint = False
            constraint_parts = key.rsplit(' ', 1)

            if len(constraint_parts) == 2:
                constraint_key, constraint_name = constraint_parts

                # known constraint?
                if constraint_name in self.constraints:
                    constraint = self.constraints[constraint_name](value)

                    # key already in the dict? combine with the previous constraint:
                    if constraint_key in constraints:
                        constraint = WrapConstraintsAnd(constraint, constraints[constraint_key])

                    constraints[constraint_key] = constraint
                    is_constraint = True

            # regular matcher:
            if not is_directive and not is_constraint:

                # all keys?
                if key == value == '*':
                    include_all_keys = True
                    continue

                # optional?
                if len(key) > 1 and key.endswith('?'):
                    key = key[:-1]
                    optional_keys.add(key)
                    matchers[key] = self.compile(value)
                    continue

                # normal key/value match:
                matchers[key] = self.compile(value)

        return MatchDict(matchers, constraints, directives, optional_keys, include_all_keys)

    def compile_list(self, pattern):
        """
        Lists are compiled into either MatchEmptyList or MatchList instances.
        """
        # optimize empty patterns:
        if pattern == []:
            return MatchEmptyList()

        matchers = [self.compile(value) for value in pattern]
        return MatchList(matchers)


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
    content = text.encode('utf-8')
    sys.stdout.buffer.write(content)


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
    print(line, flush = True)


def errln(line):
    """ Write 'line' to stderr, using the platform encoding and newline format. """
    print('MQLite.py: error:', line, file = sys.stderr, flush = True)


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

