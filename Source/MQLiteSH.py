#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MQLiteSH.
An interactive shell for MQLite.
"""


import os
import json
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter


# Information and error messages:

def outln(line):
    """ Write 'line' to stdout, using the platform encoding and newline format. """
    print(line)


def errln(line):
    """ Write 'line' to stderr, using the platform encoding and newline format. """
    print(line, file = sys.stderr)


# Non-builtin imports:

try:
    from MQLite import JSONFormatter, JSONPattern, NoMatch

except ImportError:
    errln('MQLiteSH requires the following modules:')
    errln('MQLite 2014.08.21+ - <https://github.com/Beluki/MQLite>')
    sys.exit(1)


# IO utils:

def read_json_file(filepath):
    """
    Open 'filepath' as UTF-8 and parse the content as JSON.
    Allows an optional BOM.
    """
    with open(filepath, encoding = 'utf-8-sig') as descriptor:
        return json.load(descriptor)


# A simple read-eval-print-loop:

class REPL(object):

    def __init__(self, data, formatter):
        self.data = data
        self.formatter = formatter

        self.intro = 'MQLite interactive shell (EOF to exit)'
        self.prompt = '>>> '

    def eval(self, text):
        """
        Parse and execute a given pattern against our data.
        """
        return JSONPattern(text).match(self.data)

    def print_json(self, jsondata):
        """
        Print 'jsondata' as text to stdout using our formatter options.
        """
        self.formatter.stdout(jsondata)

    def run(self):
        """
        Start the read-eval-print-loop.
        """
        outln(self.intro)

        while True:
            try:
                line = input(self.prompt)

                if line:
                    result = self.eval(line)

                    if not result is NoMatch:
                        self.print_json(result)
                        outln('')

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
        usage  = 'MQLiteSH.py filepath [option [options ...]]')

    # required:
    parser.add_argument('filepath',
        help = 'JSON file to use as input data on the REPL',
        metavar = 'filepath')

    # same output options as in MQLite itself
    # except that the REPL always uses os.linesep:
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

    return parser


# Entry point:

def main():
    parser = make_parser()
    options = parser.parse_args()

    indent = options.indent
    if options.indent < 0:
        indent = None

    # read the input file:
    jsondata = None

    try:
        jsondata = read_json_file(options.filepath)

    except Exception as err:
        errln(str(err))
        sys.exit(1)

    # start the repl:
    formatter = JSONFormatter(options.ascii, indent, options.sort_keys, os.linesep)
    repl = REPL(jsondata, formatter)
    repl.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

