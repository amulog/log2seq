#!/usr/bin/env python

from log2seq import LogParser
from log2seq import preset
from log2seq.header import *
from log2seq.statement import *


header_rule1 = [
    ItemGroup([Digit("month"),
               Digit("day"),
               Time()], separator=" ."),
    UserItem("env", r"[a-zA-Z0-9._* ]+", strip=" "),
    Statement()
]

header_rule2 = [
    ItemGroup([Digit("month"),
               Digit("day"),
               Time()], separator=" ."),
    Statement()
]

defaults = {"year": datetime.datetime.now().year}

header_parser1 = HeaderParser(header_rule1, separator="[]- ", defaults=defaults)
header_parser2 = HeaderParser(header_rule2, separator="[] ", defaults=defaults)

statement_parser = preset.default_statement_parser()

parser = LogParser([header_parser1, header_parser2], statement_parser)

