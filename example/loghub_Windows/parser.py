#!/usr/bin/env python

from log2seq import LogParser
from log2seq import preset
from log2seq.header import *
from log2seq.statement import *


header_rule = [
    ItemGroup([Date()], separator=""),
    Time(),
    String("level"),
    String("component"),
    Statement()
]

header_parser = HeaderParser(header_rule, separator=" ,\t")

pattern_windows_fullpath = r"[A-Z]:(\\[a-zA-Z0-9.*?_-])+"

statement_rules = [
    Split('"' + "()[]{}|+',=><;`# "),
    FixIP(),
    Fix([preset.pattern_time,
         preset.pattern_macaddr,
         pattern_windows_fullpath]),
    Split(":")
]

statement_parser = StatementParser(statement_rules)

parser = LogParser(header_parser, statement_parser)

