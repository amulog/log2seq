#!/usr/bin/env python

import sys

import click


def text_postprocess(line):
    return line.rstrip("\r\n")


def bin_postprocess(line, encoding="utf-8"):
    return line.decode(encoding).rstrip("\r\n")


def iter_lines(files, encoding="utf-8"):
    if len(files) == 0:
        for line in sys.stdin:
            yield text_postprocess(line)
    else:
        for fp in files:
            # tar archives (optionally compressed); check before the plain
            # .gz/.bz2 cases so that e.g. "x.tar.gz" is read as a tar, not gzip.
            # tarfile.open(mode="r") auto-detects the compression.
            if fp.endswith((".tar", ".tar.gz", ".tgz",
                            ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
                import tarfile
                with tarfile.open(fp, 'r') as tar:
                    for info in tar.getmembers():
                        if info.isfile():
                            with tar.extractfile(info) as f:
                                for line in f:
                                    yield bin_postprocess(line, encoding=encoding)
            elif fp.endswith(".bz2"):
                import bz2
                with bz2.open(fp, 'rt', encoding=encoding) as f:
                    for line in f:
                        yield text_postprocess(line)
            elif fp.endswith(".gz"):
                import gzip
                with gzip.open(fp, 'r') as f:
                    for line in f:
                        yield bin_postprocess(line, encoding=encoding)
            else:
                with open(fp, 'rt', encoding=encoding) as f:
                    for line in f:
                        yield text_postprocess(line)


def format_parsed_line(pline, format_type):
    if format_type == "object":
        return str(pline)
    elif format_type == "words":
        return " ".join(pline["words"])
    else:
        raise ValueError("invalid format type: {0}".format(format_type))


def format_parsed_statement(words, separators, format_type):
    if format_type == "object":
        return str((words, separators))
    elif format_type == "words":
        return " ".join(words)
    else:
        raise ValueError("invalid format type: {0}".format(format_type))


@click.command()
@click.argument("files", nargs=-1)
@click.option("--parser", "-p", default=None,
              help="filename of parser script (default: built-in parser)")
@click.option("--encoding", default="utf-8",
              help="encoding to load input data")
@click.option("--output", "-o", default=None,
              help="output filename for results (default: stdout)")
@click.option("--type", "-t", "format_type",
              type=click.Choice(["object", "words"]), default="object",
              help="output format type")
@click.option("--statement", "-s", "as_statement", is_flag=True,
              help="parse input as a statement (without header)")
@click.option("--failures-only", "failures_only", is_flag=True,
              help="suppress successful results; show only failures and summary")
@click.option("--max-failures", "max_failures", type=int, default=5,
              help="max failed lines to report to stderr (0 for unlimited)")
@click.option("--show-input", "-i", "show_input", is_flag=True,
              help="prefix each successful result with the input line")
@click.option("--verbose", "-v", is_flag=True,
              help="verbose parse progress to stderr")
def main(files, parser, encoding, output, format_type, as_statement,
         failures_only, max_failures, show_input, verbose):
    """Parse log messages from FILES (or stdin if FILES not given).

    Successful results are written to stdout (so they can be piped); parse
    failures and a final summary are written to stderr. Exit status is 0 when
    at least one line is parsed, 1 when nothing parses, and 2 on a startup
    error (e.g. the parser script or input cannot be loaded).
    """
    from .preset import default
    from log2seq._common import load_parser_script, LogParseFailure

    if parser:
        try:
            lp = load_parser_script(parser)
        except Exception as e:
            raise click.UsageError(
                "cannot load parser script {0}: {1}".format(parser, e))
    else:
        lp = default()

    f_output = open(output, "w", encoding=encoding) if output else sys.stdout
    n_ok = n_fail = 0
    try:
        for line in iter_lines(files, encoding=encoding):
            if line == "":
                continue
            try:
                if as_statement:
                    words, seps = lp.process_statement(line, verbose=verbose)
                    result = format_parsed_statement(words, seps, format_type)
                else:
                    pline = lp.process_line(line, verbose=verbose)
                    if pline is None:
                        continue
                    result = format_parsed_line(pline, format_type)
            except LogParseFailure as e:
                n_fail += 1
                if max_failures <= 0 or n_fail <= max_failures:
                    click.echo("parse failed: {0!r}: {1}".format(line, e),
                               err=True)
                elif n_fail == max_failures + 1:
                    click.echo("... (further failures suppressed; "
                               "use --max-failures 0 to show all)", err=True)
                continue
            n_ok += 1
            if not failures_only:
                if show_input:
                    click.echo(line, file=f_output)
                click.echo(result, file=f_output)
    except OSError as e:
        raise click.UsageError("cannot read input: {0}".format(e))
    finally:
        if output:
            f_output.close()

    click.echo("# processed {0} lines: {1} ok, {2} failed".format(
        n_ok + n_fail, n_ok, n_fail), err=True)
    if n_ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
