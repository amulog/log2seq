#!/usr/bin/env python

from log2seq import LogParser
from log2seq import preset
from log2seq.header import *
from log2seq.statement import *


# As the HeaderApp logs include date in abbreviated digit format without separators,
# this example do not parse datetime but leave it as is.
# (e.g., we cannot determine 2018111 as Jan 11 or Nov 1 in per-line analysis)

header_rule = [
    ItemGroup([
        UserItem("datestring", "[0-9]+"),  # instead, DateConcat() is ok for HealthApp_2k.log
        Digit("hour"),
        Digit("minute"),
        Digit("second"),
        DemicalSecond()],separator=":-"),
    UserItem("component", r"[a-zA-Z0-9_]+"),
    Digit("processid"),
    Statement()
]

header_parser = HeaderParser(header_rule, separator="|", reformat_timestamp=False)

statement_parser = preset.default_statement_parser()

parser = LogParser(header_parser, statement_parser)

