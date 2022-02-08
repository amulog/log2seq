#!/usr/bin/env python

import sys

import click


def format_parsed_line(pline, format_type):
    if format_type == "object":
        return str(pline)
    elif format_type == "words":
        return " ".join(pline["words"])


def format_parsed_statement(words, separators, format_type):
    if format_type == "object":
        return str((words, separators))
    elif format_type == "words":
        return " ".join(words)


@click.command()
@click.argument("files", nargs=-1)
@click.option("--parser", "-p", default=None,
              help="filename of parser script")
@click.option("--output", "-o", default=None,
              help="output filename")
@click.option("--type", "-t", "format_type", default="object",
              help="output format type, one of [object, words]")
@click.option("--as-statement", "-s", "as_statement", is_flag=True,
              help="consider input as statement (without header)")
@click.option("--verbose", "-v", is_flag=True,
              help="verbose output to stderr")
def main(files, parser, output, format_type, as_statement, verbose):

    if format_type not in ("object", "words"):
        click.BadParameter("invalid type")

    from .preset import default, load_parser_script
    if parser:
        lp = load_parser_script(parser)
    else:
        lp = default()

    if output:
        f_output = open(output, "w")
    else:
        f_output = sys.stdout

    for file in files:
        with open(file, "r") as f:
            for line in f:
                if line.rstrip() == "":
                    continue

                if as_statement:
                    words, seps = lp.process_statement(line, verbose=verbose)
                    buf = format_parsed_statement(words, seps, format_type)
                else:
                    pline = lp.process_line(line, verbose=verbose)
                    buf = format_parsed_line(pline, format_type)

                f_output.write(buf)

    f_output.close()


if __name__ == "__main__":
    main()
