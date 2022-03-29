#!/usr/bin/env python
# coding: utf-8

from log2seq import LogParser
from log2seq import preset
from log2seq.header import *
from log2seq.statement import *


header_rule1 = [
    MonthAbbreviation(),
    Digit("day"),
    Time(),
    Hostname("host"),
    UserItem("component", r"[a-zA-Z0-9._-]+"),
    Digit("processid", optional=True),
    Statement()
]

header_rule2 = [
    MonthAbbreviation(),
    Digit("day"),
    Time(),
    UserItem("dummy", r"---"),
    Statement()
]

header_rule3 = [
    Statement()
]

defaults = {"year": datetime.datetime.now().year,
            "host": None}

header_parser1 = HeaderParser(header_rule1, separator=" :[]", defaults=defaults)
header_parser2 = HeaderParser(header_rule2, separator=" :[]", defaults=defaults)
header_parser3 = HeaderParser(header_rule3, separator=" \t", reformat_timestamp=False)

statement_parser = preset.default_statement_parser()

parser = LogParser([header_parser1, header_parser2, header_parser3], statement_parser)

