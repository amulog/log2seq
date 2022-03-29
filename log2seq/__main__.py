#!/usr/bin/env python

import sys

import click


def text_postprocess(line):
    return line.rstrip("\r\n")


def bin_postprocess(line, encoding="utf-8"):
    return line.decode(encoding).rstrip("\r\n")


def iter_lines(files, encoding="utf-8"):
    if len(files) == 0:
        for line in sys.stdin.readlines():
            yield text_postprocess(line)
    else:
        for fp in files:
            if ".tar." in fp:
                import tarfile
                with tarfile.open(fp, 'r') as tar:
                    for info in tar.getmembers():
                        if info.isfile():
                            with tar.extractfile(info) as f:
                                for line in f.readlines():
                                    yield bin_postprocess(line, encoding=encoding)
            elif fp.endswith(".bz2"):
                import bz2
                with bz2.open(fp, 'rt', encoding=encoding) as f:
                    for line in f.readlines():
                        yield text_postprocess(line)
            elif fp.endswith(".gz"):
                import gzip
                with gzip.open(fp, 'r') as f:
                    for line in f.readlines():
                        yield bin_postprocess(line, encoding=encoding)
            else:
                with open(fp, 'rt', encoding=encoding) as f:
                    for line in f.readlines():
                        yield text_postprocess(line)


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
@click.option("--encoding", default="utf-8",
              help="encoding to load input data")
@click.option("--output", "-o", default=None,
              help="output filename")
@click.option("--type", "-t", "format_type", default="object",
              help="output format type, one of [object, words]")
@click.option("--show-input", "-i", "show_input", is_flag=True,
              help="additionally show the input string line as is")
@click.option("--as-statement", "-s", "as_statement", is_flag=True,
              help="consider input as statement (without header)")
@click.option("--verbose", "-v", is_flag=True,
              help="verbose output to stderr")
def main(files, parser, encoding, output, format_type, show_input, as_statement, verbose):
    """Parse log messages given in FILES (or stdin if FILES not given)."""

    if format_type not in ("object", "words"):
        click.BadParameter("invalid type")

    from .preset import default
    from log2seq._common import load_parser_script
    if parser:
        lp = load_parser_script(parser)
    else:
        lp = default()

    if output:
        f_output = open(output, "w")
    else:
        f_output = sys.stdout

    for line in iter_lines(files, encoding=encoding):
        if line != "":
            if show_input:
                f_output.write(line + "\n")
            if as_statement:
                words, seps = lp.process_statement(
                    line, verbose=verbose
                )
                buf = format_parsed_statement(words, seps, format_type)
            else:
                pline = lp.process_line(line, verbose=verbose)
                buf = format_parsed_line(pline, format_type)

            f_output.write(buf + "\n")

    f_output.close()


if __name__ == "__main__":
    main()
