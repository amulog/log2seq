# coding: utf-8

"""log2seq.preset is a submodule to provide some settings
for frequently used log formats."""


from ._common import LogParser
from .header import *
from .statement import *

PARSER_OBJECT_NAME = "parser"

pattern_time = r"^\d{2}:\d{2}:\d{2}(\.\d+)?$"
pattern_macaddr = r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"


def default_header_parsers():
    """Generate list of :class:`~log2seq.header.HeaderParser` with default settings.

    The default header parsers consists of 2 different rules.

    * Rule 1 (designed for syslogd default format)

        * year (:class:`~header.Digit`, optional)
        * month (:class:`~log2seq.header.MonthAbbreviation`)
        * day (:class:`~log2seq.header.Digit`)
        * time (:class:`~log2seq.header.Time`)
        * host (:class:`~log2seq.header.String`)
        * statement (:class:`~log2seq.header.Statement`)

    * Rule 2 (designed for default asctime format of python logging)

        * date (:class:`~log2seq.header.Date`)
        * time (:class:`~log2seq.header.Time`)
        * host (:class:`~log2seq.header.String`)
        * statement (:class:`~log2seq.header.Statement`)

    Returns:
        list of :class:`~log2seq.header.HeaderParser`
    """
    import datetime
    header_rules = [[Digit("year", optional=True),
                     MonthAbbreviation(),
                     Digit("day"),
                     Time(),
                     Hostname("host"),
                     Statement()],
                    [Date(),
                     Time(),
                     Hostname("host"),
                     Statement()]]
    defaults = {"year": datetime.datetime.now().year}
    return [HeaderParser(rule, defaults=defaults) for rule in header_rules]


def default_statement_parser():
    """Generate :class:`~log2seq.statement.StatementParser`
    with default settings.

    The default parser consists of 4 step actions.

    #. :class:`~log2seq.statement.Split` with standard symbols including white space and parenthesis
    #. :class:`~log2seq.statement.FixIP` to fix IP addresses (including network address)
    #. :class:`~log2seq.statement.Fix` with timestamps and MAC addresses
    #. :class:`~log2seq.statement.Split` with :samp:`:`

    Returns:
        :class:`~log2seq.statement.StatementParser`
    """
    statement_rules = [
        Split('"' + "()[]{}|+',=><;`# "),
        FixIP(),
        Fix([pattern_time, pattern_macaddr]),
        Split(":")
    ]
    return StatementParser(statement_rules)


def default():
    """Generates :class:`~log2seq.LogParser` of default settings.

    It consists of :func:`default_header_parsers`
    and :func:`default_statement_parser`.
    :func:`~log2seq.init_parser` generates same instance without any arguments.

    Returns:
        :class:`~log2seq.LogParser`
    """
    return LogParser(default_header_parsers(),
                     default_statement_parser())


def apache_errorlog_parser():
    header_rule1 = [
        String("weekday", dummy=True),
        MonthAbbreviation(),
        Digit("day"),
        Time(),
        Digit("year"),
        String("severityname"),
        UserItem("client", r"client", optional=True, dummy=True),
        Hostname("host", optional=True),
        Statement()
    ]
    separator1 = " []"
    p1 = HeaderParser(header_rule1, separator=separator1)

    header_rule2 = [
        String("weekday", dummy=True),
        MonthAbbreviation(),
        Digit("day"),
        Time(),
        Digit("year"),
        UserItem("core", r"core", dummy=True),
        String("severityname"),
        UserItem("pid", r"pid", dummy=True),
        Digit("processid"),
        UserItem("tid", r"tid", dummy=True),
        Digit("threadid"),
        UserItem("client", r"client", optional=True, dummy=True),
        Hostname("host", optional=True),
        Statement()
    ]
    separator2 = " []:"
    p2 = HeaderParser(header_rule2, separator=separator2)

    return LogParser([p1, p2],
                     default_statement_parser())


def load_parser_script(script_filepath):
    import sys
    import os.path
    from importlib import import_module

    # add script to sys.path
    path = os.path.dirname(script_filepath)
    sys.path.append(os.path.abspath(path))

    # import dynamically
    libname = os.path.splitext(os.path.basename(script_filepath))[0]
    script_mod = import_module(libname)

    # obtain parser object
    lp = getattr(script_mod, PARSER_OBJECT_NAME)
    return lp
