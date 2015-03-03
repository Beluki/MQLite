
## About

MQLite is a small pattern matching language loosely based on [MQL][], the
Metaweb Query Language. The main difference is that MQLite can be used
to pattern match arbitrary JSON data instead of a particular schema (such
as Freebase).

[MQLite][] is a simple program, it reads JSON from stdin and outputs JSON to
stdout. The pattern is specified as a parameter. Here is an example,
using the Github API to find repositories that have forks:

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

Also included is [MQLiteSH][], an interactive shell that can be used to easily
query local JSON files.

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
here and there (needed to match arbitrary JSON). The best way to learn it is
by example.

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

* null matches anything.

* booleans, numbers and strings match themselves.

* lists match another list if each element in the query list
  matches at least one element of the data list.

* dicts match another dict if all the keys in the query dict
  are present in the data and the values for those keys match.

Here are some examples (using MQLiteSH with the above dataset as input)

```
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

* \>, >=, <, <=, ==, != compare data with the usual arithmetic operations.

* "contain", "in" test that the data contains a value or is contained in a set of values.

* "regex" matches data against regular expressions.

* "is" tests that the data is of a particular type.

* "match" like basic pattern matching.

Constrains are written after the key name they apply to in the query dict.
Unlike basic patterns, constraints don't add anything to the final query result.

Examples:

```
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

## Status

This program is finished!

MQLite is feature-complete and has no known bugs. Unless issues are reported
I plan no further development on it other than maintenance.

## License

Like all my hobby projects, this is Free Software. See the [Documentation][]
folder for more information. No warranty though.

[Documentation]: https://github.com/Beluki/MQLite/tree/master/Documentation
[Examples]: https://github.com/Beluki/MQLite/tree/master/Examples

