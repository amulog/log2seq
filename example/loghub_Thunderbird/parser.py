#!/usr/bin/env python

from log2seq import LogParser
from log2seq import preset
from log2seq.header import *
from log2seq.statement import *


header_rule = [
    UserItem("label", r"-|[A-Z]+"),
    Digit("unixtime", dummy=True),
    ItemGroup([Digit("year"),
               Digit("month", dummy=True),
               Digit("day", dummy=True)],
               separator="."),
    UserItem("host", r"[a-zA-Z0-9:-]+"),
    MonthAbbreviation(),
    Digit("day"),
    Time(),
    UserItem("location", r"[a-zA-Z0-9/@-]+", dummy=True),
    ItemGroup([UserItem("component", r"[a-zA-Z0-9()/._-]+"),
               Digit("processid")], separator="[]:"),
    Statement()
]

header_parser = HeaderParser(header_rule)

statement_parser = preset.default_statement_parser()

parser = LogParser(header_parser, statement_parser)

