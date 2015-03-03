
## About

MQLite is a small pattern matching language loosely based on [MQL][], the
Metaweb Query Language. The main difference is that MQLite can be used
to pattern match arbitrary JSON data instead of a particular schema (such
as Freebase).

[MQL]: http://mql.freebaseapps.com/index.html

MQLite is a simple program, it reads JSON from stdin and outputs JSON to
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

Also included is MQLiteSH, an interactive shell that can be used to easily
query local JSON files.

## Status

This program is finished!

MQLite is feature-complete and has no known bugs. Unless issues are reported
I plan no further development on it other than maintenance.

## License

Like all my hobby projects, this is Free Software. See the [Documentation][]
folder for more information. No warranty though.

[Documentation]: https://github.com/Beluki/MQLite/tree/master/Documentation
[Examples]: https://github.com/Beluki/MQLite/tree/master/Examples

