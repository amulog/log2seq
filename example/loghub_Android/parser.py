#!/usr/bin/env python

from log2seq import LogParser
from log2seq import preset
from log2seq.header import *
from log2seq.statement import *


header_rule = [
    ItemGroup([Digit("month"), Digit("day")], separator="-"),
    Time(),
    Digit("pid"),
    Digit("tid"),
    UserItem("level", r"[A-Z]"),
    Statement()
]

defaults = {"year": datetime.datetime.now().year}
header_parser = HeaderParser(header_rule, separator=":\t ", defaults=defaults)

statement_parser = preset.default_statement_parser()

parser = LogParser(header_parser, statement_parser)

