#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import sys

from MQLite import NoMatch, Pattern


# Input:

DATA = [
    {
        "name": "Anna",
        "age": 25,
        "student": True,
        "grades": { "chemistry": "A", "math": "C" },
        "hobbies": ["reading", "chess", "swimming"]
    },
    {
        "name": "James",
        "age": 23,
        "student": False,
        "hobbies": ["chess", "football", "basketball"]
    },
    {
        "name": "John",
        "age": 35,
        "student": True,
        "grades": { "chemistry": "C", "english": "A" },
        "hobbies": ["reading", "swimming", "painting"]
    }
]


# Tests:

class Test1(object):
    """
    Simple pattern.
    """
    pattern = [{ "name": None }]
    result = [{"name": "Anna"}, {"name": "James"}, {"name": "John"}]

class Test2(object):
    """
    Simple pattern.
    """
    pattern = [{ "name": None, "student": True }]
    result = [{"name": "Anna", "student": True}, {"name": "John", "student": True}]

class Test3(object):
    """
    Regex.
    """
    pattern = [{ "age": None, "name regex": "^A", "name": None }]
    result = [{"name": "Anna", "age": 25}]

class Test4(object):
    """
    Contain.
    """
    pattern = [{ "name": None, "hobbies contain": "chess" }]
    result = [{"name": "Anna"}, {"name": "James"}]

class Test5(object):
    """
    Multiple constraints for the same key.
    """
    pattern = [{ "age": None, "age >": 20, "age <": 30, "age !=": 25 }]
    result = [{"age": 23}]

class Test6(object):
    """
    In.
    """
    pattern = [{ "name": None, "age in": [23, 25] }]
    result = [{"name": "Anna"}, {"name": "James"}]

class Test7(object):
    """
    Multiple constraints, not prefix.
    """
    pattern = [{ "name": None, "age !=": 25, "hobbies not contain": "chess" }]
    result = [{"name": "John"}]

class Test8(object):
    """
    Any suffix, * directive.
    """
    pattern = [{ "name in any": ["John", "Beth", "Anna"], "*": ["name"] }]
    result = [{"name": "Anna"}, {"name": "John"}]

class Test9(object):
    """
    All suffix, One suffix.
    """
    pattern = [{ "hobbies contain all": ["chess", "football"], "hobbies": None, "name == one": ["Anna", "James"] }]
    result = [{"hobbies": ["chess", "football", "basketball"]}]

class Test10(object):
    """
    Multiple matchers in a list.
    """
    pattern = [{ "name": None }, {"age": 23, "name": None }]
    result = [{"name": "Anna"}, {"name": "James"}, {"name": "John"}, {"name": "James", "age": 23}]

class Test11(object):
    """
    __sort__ + __limit__ directives.
    """
    pattern = collections.OrderedDict(hobbies = None, age = None)

    # order dependent, we want __sort__ to happen before __limit__:
    pattern["__sort__"] = "age"
    pattern["__limit__"] = 1

    pattern = [pattern]
    result = [{"hobbies": ["chess", "football", "basketball"], "age": 23}]

class Test12(object):
    """
    Recursive matching (dict inside dict).
    """
    pattern = [{ "grades": { "chemistry in": ["A", "B"], "*": "*" }, "*": ["name"] }]
    result = [{"name": "Anna", "grades": {"math": "C", "chemistry": "A"}}]

class Test13(object):
    """
    __order__: reverse.
    """
    pattern = [{ "name": None, "__order__": "reverse" }]
    result = [{"name": "John"}, {"name": "James"}, {"name": "Anna"}]

class Test14(object):
    """
    Both prefix + suffix.
    """
    pattern = [{ "hobbies not contain any": ["chess", "basketball", "football"], "name": None }]
    result = [{"name": "John"}]

class Test15(object):
    """
    Constraint in is equivalent to match any.
    """
    pattern = [{ "name match any": ["James", "Anna"], "name": None }]
    result = [{"name": "Anna"}, {"name": "James"}]

class Test16(object):
    """
    Constraint contain is equivalent to match.
    """
    pattern = [{ "hobbies match": ["basketball"], "name": None }]
    result = [{"name": "James"}]

class Test17(object):
    """
    Only constraints returns an empty dict.
    """
    pattern = [{ "age >": 0 }]
    result = [{}, {}, {}]

class Test18(object):
    """
    "*" can be matched with constraint ==.
    """
    pattern = [{ "* ==": "*" }]
    result = NoMatch

class Test19(object):
    """
    != and == use Python booleans, equivalent to 0 and 1.
    """
    pattern = [{ "age": None, "age <": 30, "student !=": 1 }]
    result = [{"age": 23}]

class Test20(object):
    """
    Unknown datatypes are matched by default with Python equality.
    """
    pattern = [{ "name": None, "age in": set([20, 21, 22, 23]) }]
    result = [{"name": "James"}]


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using the platform encoding and newline format. """
    print(line, flush = True)


def errln(line):
    """ Write 'line' to stderr, using the platform encoding and newline format. """
    print(line, file = sys.stderr, flush = True)


# Run the tests:

def main():
    tests = [value() for key, value in globals().items() if key.startswith('Test')]
    errors = 0

    for test in tests:
        pattern = Pattern(test.pattern)
        result = pattern.match(DATA)

        if result != test.result:
            errln('Test: {}'.format(test.__doc__.strip()))
            errln('Expected: {} got: {}'.format(test.result, result))
            errln('')

            errors += 1

    if errors > 0:
        errln('Errors: {}'.format(errors))
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

