# coding: utf-8

from .header import *
from .statement import *
from ._common import LogParser


pattern_time = r"^\d{2}:\d{2}:\d{2}(\.\d+)?$"
pattern_macaddr = r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"


def default_header_parsers():
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
    statement_rules = [
        Split('"' + "()[]{}|+',=><;`# "),
        FixIP(),
        Fix([pattern_time, pattern_macaddr]),
        Split(":")
    ]
    return StatementParser(statement_rules)


def default():
    return LogParser(default_header_parsers(),
                     default_statement_parser())
