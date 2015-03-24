
## About

MQLite is a small pattern matching language loosely based on [MQL][], the
Metaweb Query Language. The main difference is that MQLite can be used
to pattern match arbitrary JSON data instead of a particular schema (such
as [Freebase][]).

[MQLite][] is a simple program, it reads JSON from stdin and outputs JSON to
stdout. The pattern is specified as a parameter. Here is an example,
using the [Github API][] to find repositories that have forks:

```bash
$ curl https://api.github.com/users/Beluki/repos |
| MQlite.py '[{"name": null, "forks": null, "forks >": 0}]'
[
    {
        "name": "GaGa",
        "forks": 2
    },
    {
        "name": "MQLite",
        "forks": 1
    }
]
```

Also included is [MQLiteSH][], an interactive shell that can be used to
easily query local JSON files.

[Freebase]: https://www.freebase.com
[Github API]: https://developer.github.com/v3/
[MQL]: http://mql.freebaseapps.com/index.html
[MQLite]: https://github.com/Beluki/MQLite/blob/master/Source/MQLite.py
[MQLiteSH]: https://github.com/Beluki/MQLite/blob/master/Source/MQLiteSH.py

## Installation

MQLite and MQLiteSH are single, small Python 3.3.+ files with no dependencies
other than the Python 3 standard library. You can just put them in your PATH.

Installation is only needed to import MQLite as a library in your own programs
(e.g. custom pattern matching or extensions). This can be done using setuptools:

```bash
$ cd Source
$ python setup.py install
```

## MQLite specification

The MQLite language is very similar to the MQL read API with a few changes
here and there (needed to match arbitrary JSON). The best way to learn it
is by example.

All the examples in this README use the following JSON data as input:

```json
[
    {
        "name": "Anna",
        "age": 25,
        "student": true,
        "grades": { "chemistry": "A", "math": "C" },
        "hobbies": ["reading", "chess", "swimming"]
    },
    {
        "name": "James",
        "age": 23,
        "student": false,
        "hobbies": ["chess", "football", "basketball"]
    },
    {
        "name": "John",
        "age": 35,
        "student": true,
        "grades": { "chemistry": "C", "english": "A" },
        "hobbies": ["reading", "swimming", "painting"]
    }
]
```

Basic pattern matching rules:

* `null` matches anything.

* booleans, numbers and strings match themselves.

* lists match another list if each element in the query list
  matches at least one element of the data list.

* dicts match another dict if all the keys in the query dict
  are present in the data and the values for those keys match.

Here are some examples (using MQLiteSH with the above dataset as input).

```json
# give me the name and the age for everyone:
>>> [{ "name": null, "age": null }]
[
    {
        "age": 25,
        "name": "Anna"
    },
    {
        "age": 23,
        "name": "James"
    },
    {
        "age": 35,
        "name": "John"
   }
]

# find the names of those that are students:
>>> [{ "name": null, "student": true }]
[
    {
        "student": true,
        "name": "Anna"
    },
    {
        "student": true,
        "name": "John"
    }
]

# who plays both chess and basketball?
>>> [{ "name": null, "hobbies": ["chess", "basketball"] }]
[
    {
        "name": "James",
        "hobbies": [
            "chess",
            "basketball"
        ]
    }
]
```

## MQLite specification: constraints

Basic pattern matching only allows to test datatypes for equality. Constraints
make it possible to match on arbitrary operations.

Implemented constraints are:

* `>`, `>=`, `<`, `<=`, `==`, `!=` compare data with the usual arithmetic operations.

* `contain`, `in` test that the data contains a value or is contained in a set of values.

* `regex` matches data against regular expressions.

* `is` tests that the data is of a particular type.

* `match` recursively matches its argument.

Constrains are written after the key name they apply to in the query dict.
Unlike basic patterns, constraints don't add anything to the final query result.

Examples:

```json
# who is more than 25 years old?
>>> [{ "name": null, "age >": 25 }]
[
    {
        "name": "John"
    }
]

# give me the names of the people whose name starts with a J
>>> [{ "name": null, "name regex": "^J" }]
[
    {
        "name": "James"
    },
    {
        "name": "John"
    }
]

# what are the hobbies of John and Anna?
>>> [{ "name in": ["John", "Anna"], "name": null, "hobbies": null }]
[
    {
        "name": "Anna",
        "hobbies": [
            "reading",
            "chess",
            "swimming"
        ]
    },
    {
        "name": "John",
        "hobbies": [
            "reading",
            "swimming",
            "painting"
        ]
    }
]

# who got an A in chemistry? what's his/her math grade?
>>> [{ "name": null, "grades match": {"chemistry": "A"}, "grades": {"math": null} }]
[
    {
        "name": "Anna",
        "grades": {
            "math": "C"
        }
    }
]
```

## MQLite specification: constraint modifiers

To be able to express NOT, AND, OR and XOR, MQLite allows constraints to
be prefixed and suffixed with additional operators:

* `not` as a prefix negates the constraint.

* `all` as a suffix requires the constraint to match every item in a list
  (e.g. AND).

* `any` as a suffix requires the constraint to match at least one of the elements
  in a list (e.g. OR).

* `one` as a suffix requires the constraint to match only one of the elements
  in a list (e.g. XOR).

Examples:

```json
# whose age is not 23?
>>> [{ "name": null, "age": null, "age not ==": 23 }]
[
    {
        "name": "Anna",
        "age": 25
    },
    {
        "name": "John",
        "age": 35
    }
]

# who likes reading or painting?
>>> [{ "name": null, "hobbies contain any": ["reading", "painting"] }]
[
    {
        "name": "Anna"
    },
    {
        "name": "John"
    }
]

# who likes swimming or painting but not both?
>>> [{ "name": null, "hobbies contain one": ["swimming", "painting"] }]
[
    {
        "name": "Anna"
    }
]
```

In both MQL and MQLite it's impossible to write an OR clause using
multiple keys, e.g. `age > 20 or name in ...`. You need to write multiple
queries to do it.

Other than that it's possible to specify as many constraints as you
want for each key, with or without prefixes/suffixes.

## MQLite specification: directives

Directives are special keys that change results in a particular way.
The currently implemented directives are:

* `__limit__` returns a subset of the results.

* `__sort__` sorts the results by a given key.

* `__order__` sorts the results randomly or in reverse order.

* `*` returns all the keys in a query or a list of particular keys.

Examples:

```json
# give me a random name
>>> [{ "name": null, "__order__": "random", "__limit__": 1 }]
[
    {
        "name": "Anna"
    }
]

# give me all the names and ages, sort the results by age in reverse order
>>> [{ "name": null, "age": null, "__sort__": "age", "__order__": "reverse" }]
[
    {
        "name": "John",
        "age": 35
    },
    {
        "name": "Anna",
        "age": 25
    },
    {
        "name": "James",
        "age": 23
    }
]

# who is at least 25 years old? give me all the properties
>>> [{ "age >": 25, "*": "*" }]
[
    {
        "name": "John",
        "student": true,
        "age": 35,
        "grades": {
            "english": "A",
            "chemistry": "C"
        },
        "hobbies": [
            "reading",
            "swimming",
            "painting"
        ]
    }
]

# who got at least a B in chemistry? give me all the grades
>>> [{ "name": null, "grades": { "chemistry <=": "B", "*": "*" }}]
[
    {
        "name": "Anna",
        "grades": {
            "math": "C",
            "chemistry": "A"
        }
    }
]

# what are John's hobbies and age?
>>> [{ "name ==": "John", "*": ["hobbies", "age"] }]
[
    {
        "age": 35,
        "hobbies": [
            "reading",
            "swimming",
            "painting"
        ]
    }
]
```

Note that the order of the directives is important. If `__limit__` is specified
before `__sort__`, only the subset of the results returned by limit will be
considered for sorting. MQLite uses an [OrderedDict][] under the hood to maintain the
query order in JSON patterns.

[OrderedDict]: https://docs.python.org/3/library/collections.html#collections.OrderedDict

## Command-line options

MQLite has some options that can be used to change the behavior:

* `--strict` exits with an error message and status 1 when there are no matches
  instead of producing an empty output. Useful for scripts.

*  `--ascii` escapes non-ascii characters in output.

*  `--indent N` uses N spaces of indentation for output. Use -1 to disable
   indentation.

* `--sort-keys` sorts dictionary keys by name before printing the results.

* `--newline [dos, mac, unix, system]` changes the newline format.
  I tend to use Unix newlines everywhere, even on Windows. The default is
  `system`, which uses the current platform newline format.

MQLiteSH has the same options except `--strict` (no matches don't produce output)
and `--newline` (it always uses system newlines).

## Portability

Information and error messages are written to stdout and stderr
respectively, using the current platform newline format and encoding.

The input JSON is expected to be UTF-8. Both MQLite and MQLiteSH accept input
with or without a BOM signature.

The output JSON is always written in UTF-8 without BOM. When using the same
`--newline format`, it should be byte by byte identical between platforms.

MQLite is tested on Windows 7 and 8 and on Debian (both x86 and x86-64)
using Python 3.3+. Older versions are not supported.

## Status

This program is finished!

MQLite is feature-complete and has no known bugs. Unless issues are reported
I plan no further development on it other than maintenance.

## License

Like all my hobby projects, this is Free Software. See the [Documentation][]
folder for more information. No warranty though.

[Documentation]: https://github.com/Beluki/MQLite/tree/master/Documentation
[Examples]: https://github.com/Beluki/MQLite/tree/master/Examples

