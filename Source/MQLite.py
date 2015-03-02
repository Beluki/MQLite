#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLite.
Pattern match JSON like you query Freebase, using a simple MQL dialect.
"""


import builtins
import json
import os
import random
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
    def __init__(self, matchers, constraints, directives, additional_keys):
        self.matchers = list(matchers.items())
        self.constraints = list(constraints.items())
        self.directives = directives
        self.additional_keys = additional_keys

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
                return NoMatch

            result[key] = current

        # add all the data keys to the result if needed:
        # (the compiler guarantees that the value is either '*' or a list)
        if self.additional_keys == '*':
            for key, value in data.items():
                if not key in result:
                    result[key] = value
        else:
            for key in self.additional_keys:
                if key in data and not key in result:
                    result[key] = data[key]

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

            # apply directives for dictionaries:
            if isinstance(matcher, MatchDict):
                for directive in matcher.directives:
                    matcher_results = directive.match(matcher_results)

            # at least one match?
            if len(matcher_results) == 0:
                return NoMatch

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
    Tests that the data is NOT equal to a particular value.
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


class ConstraintIn(object):
    """
    Tests that the data is equal to at least one element of a list of values.
    (operator "in" in MQLite)
    """
    def __init__(self, values):
        self.values = values

    def match(self, data):
        return data in self.values


class ConstraintContain(object):
    """
    Tests that the data contains one value.
    (operator "contain" in MQLite)
    """
    def __init__(self, value):
        self.value = value

    def match(self, data):
        return self.value in data


class ConstraintIs(object):
    """
    Tests that the data belongs to a particular type.
    (operator "is" in MQLite)
    """
    def __init__(self, class_or_classname):

        # a string means a builtin type:
        if isinstance(class_or_classname, str):
            self.theclass = getattr(builtins, class_or_classname)

        # something isinstance already understands
        # (JSON has no classes but we accept them for raw Python patterns):
        else:
            self.theclass = class_or_classname

    def match(self, data):
        return isinstance(data, self.theclass)


class ConstraintMatch(object):
    """
    Tests that the data can be matched with a matcher node.
    (operator "match" in MQLite)
    """
    def __init__(self, matcher):
        self.matcher = matcher

    def match(self, data):
        return self.matcher.match(data) is not NoMatch


# Constraint prefixes:

class ConstraintPrefixNot(object):
    """
    Negates a constraint.
    """
    def __init__(self, constraint):
        self.constraint = constraint

    def match(self, data):
        return not self.constraint.match(data)


# Constraint suffixes:

class ConstraintSuffixAll(object):
    """
    Matches if all the constraints in a list match some data.
    """
    def __init__(self, constraints):
        self.constraints = constraints

    def match(self, data):
        for constraint in self.constraints:
            if not constraint.match(data):
                return False

        return True


class ConstraintSuffixAny(object):
    """
    Matches if at least one of the constraints in a list match some data.
    """
    def __init__(self, constraints):
        self.constraints = constraints

    def match(self, data):
        for constraint in self.constraints:
            if constraint.match(data):
                return True

        return False


class ConstraintSuffixOne(object):
    """
    Matches if only one of the constraints in a list match some data.
    """
    def __init__(self, constraints):
        self.constraints = constraints

    def match(self, data):
        one_matched = False

        for constraint in self.constraints:
            if constraint.match(data):
                if one_matched:
                    return False

                one_matched = True

        return one_matched


# Directives:
# Nodes that transform results into something else.
# Directives must validate their input values.

class DirectiveLimit(object):
    """
    Take N elements from the results.
    """
    def __init__(self, limit):
        self.limit = limit

    def match(self, data):
        return data[0 : self.limit]


class DirectiveOrder(object):
    """
    Return results in reverse or random order.
    """
    def __init__(self, order):
        if not order in ['random', 'reverse']:
            raise CompilerException('__order__: expected "random" or "reverse" as argument.')

        self.order = order

    def match(self, data):
        if self.order == 'random':
            random.shuffle(data)
            return data

        if self.order == 'reverse':
            data.reverse()
            return data


class DirectiveSort(object):
    """
    Sort results by a given key.
    """
    def __init__(self, key):
        self.key = key

    def match(self, data):
        return sorted(data, key = lambda value: value[self.key])


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


# Compiler utils:

def split_suffix_word(text, words):
    """
    Split "this is a text word" into ["this is a text", "word"]
    using a list of possible words.
    """
    for word in words:
        # make sure there is one space separating the word
        if text.endswith(' ' + word):
            return text.rsplit(' ', 1)

    return text, ''


# Compiler:

class CompilerException(Exception):
    pass


class Compiler(object):
    """
    The MQLite compiler.
    """
    constraints = {
        '>'       :  ConstraintMoreThan,
        '>='      :  ConstraintMoreOrEqualTo,
        '<'       :  ConstraintLessThan,
        '<='      :  ConstraintLessOrEqualTo,
        '=='      :  ConstraintEqualTo,
        '!='      :  ConstraintNotEqualTo,
        'regex'   :  ConstraintRegex,
        'in'      :  ConstraintIn,
        'contain' :  ConstraintContain,
        'is'      :  ConstraintIs,
        'match'   :  ConstraintMatch,
    }


    constraint_prefixes = {
        'not': ConstraintPrefixNot,
    }


    constraint_suffixes = {
        'all': ConstraintSuffixAll,
        'any': ConstraintSuffixAny,
        'one': ConstraintSuffixOne,
    }


    directives = {
        '__limit__' : DirectiveLimit,
        '__order__' : DirectiveOrder,
        '__sort__'  : DirectiveSort,
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

        # not a JSON type:
        return self.compile_unknown(pattern)

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
        additional_keys = []

        for key, value in pattern.items():

            # * wildcard?
            if key == '*':
                if value == '*' or isinstance(value, list):
                    additional_keys = value
                else:
                    raise CompilerException('*: value must be "*" (all keys) or a list of keys.')
                continue

            # directive?
            if key in self.directives:
                directive = self.directives[key](value)
                directives.append(directive)
                continue

            # constraint?
            constraint_key, suffix = split_suffix_word(key, self.constraint_suffixes.keys())
            constraint_key, constraint_name = split_suffix_word(constraint_key, self.constraints.keys())
            constraint_key, prefix = split_suffix_word(constraint_key, self.constraint_prefixes.keys())

            if constraint_key and constraint_name:
                constraint_class = self.constraints[constraint_name]

                # suffix?
                if suffix:
                    if not isinstance(value, list):
                        raise CompilerException('{} expected a list of values.'.format(suffix))

                    if constraint_class == ConstraintMatch:
                        values = [self.compile(it) for it in value]
                    else:
                        values = value

                    suffix_class = self.constraint_suffixes[suffix]
                    constraint = suffix_class([constraint_class(it) for it in values])

                # no suffix, value is a single element:
                else:
                    if constraint_class == ConstraintMatch:
                        value = self.compile(value)

                    constraint = constraint_class(value)

                # prefix?
                if prefix:
                    prefix_class = self.constraint_prefixes[prefix]
                    constraint = prefix_class(constraint)

                # key already in the dict? combine with the previous constraint:
                if constraint_key in constraints:
                    constraint = WrapConstraintsAnd(constraint, constraints[constraint_key])

                constraints[constraint_key] = constraint
                continue

            # regular matcher:
            matchers[key] = self.compile(value)

        return MatchDict(matchers, constraints, directives, additional_keys)

    def compile_list(self, pattern):
        """
        Lists are compiled into either MatchEmptyList or MatchList instances.
        """
        # optimize empty patterns:
        if pattern == []:
            return MatchEmptyList()

        matchers = [self.compile(value) for value in pattern]
        return MatchList(matchers)

    def compile_unknown(self, pattern):
        """
        Not a JSON type, rely on Python equality (e.g. for datetime).
        """
        return MatchEqual(pattern)


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

