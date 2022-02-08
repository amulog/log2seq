import unittest

from log2seq.statement import *


class TestStatement(unittest.TestCase):

    def test_default(self):
        input_mes = "system[12345]: host 2001:0db8:1234::1 (interface:eth0) disconnected"

        from log2seq.preset import default_statement_parser
        sp = default_statement_parser()
        l_w, l_s = sp.process_line(input_mes)

        assert l_w == ["system", "12345", "host", "2001:0db8:1234::1", "interface",
                       "eth0", "disconnected"]
        assert l_s == ["", "[", "]: ", " ", " (", ":", ") ", ""]

    def test_empty(self):
        input_mes = " "

        from log2seq.preset import default_statement_parser
        sp = default_statement_parser()
        l_w, l_s = sp.process_line(input_mes)

        assert l_w == []
        assert l_s == [" "]

    def test_ipaddr(self):
        input_mes = "tests: src :: is not link-local"
        statement_rules = [
            Split(" "),
            FixIP(),
            Split(":")
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["tests", "src", "::", "is", "not", "link-local"]

    def test_remove(self):
        input_mes = "a -> b"
        statement_rules = [
            Split(" >"),
            Remove("[^a-zA-Z0-9]+")
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["a", "b"]

    def test_fix_partial(self):
        input_mes = "source 192.0.2.1.80 initialized."
        statement_rules = [
            Split(" "),
            FixPartial(r'^(?P<ipaddr>(\d{1,3}\.){3}\d{1,3})\.(?P<port>\d{1,5})$',
                       fix_groups=["ipaddr", "port"]),
            Split(".")
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["source", "192.0.2.1", "80", "initialized"]

    def test_fix_parenthesis(self):
        input_mes = 'comment added: "This is a comment description" "This is second desc".'
        statement_rules = [
            FixParenthesis(['"', '"']),
            FixParenthesis(['"', '"']),
            Split(' .:"')
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["comment", "added", "This is a comment description", "This is second desc"]

        statement_rules = [
            FixParenthesis(['"', '"'], recursive=True),
            Split(' .:"')
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["comment", "added", "This is a comment description", "This is second desc"]

    def test_remove_partial(self):
        input_mes = "2000 Mar 4 12:34:56.789: host: :: and 127.0.0.1 duplicated timestamp given."
        statement_rules = [
            Split(" "),
            RemovePartial(r'^.*[^:](?P<colon>:)$',
                          remove_groups=["colon"]),
            RemovePartial(r'^.*[^.](?P<dot>\.)$',
                          remove_groups=["dot"]),
            Fix(r'^\d{2}:\d{2}:\d{2}\.\d{3}$'),
            FixIP(),
            Split(":")
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["2000", "Mar", "4", "12:34:56.789",
                       "host", "::", "and", "127.0.0.1", "duplicated", "timestamp", "given"]

    def test_conditional_split(self):
        input_mes = "%KERNEL-4-EVENT-7: host h1-i2.example.org scored -0.035 value (20.0%)"
        statement_rules = [
            Split(" ()"),
            RemovePartial(r'^.*[^:](?P<colon>:)$',
                          remove_groups=["colon"]),
            ConditionalSplit(r'^%[A-Z]+-\d+(-[A-Z]+-\d+)?$', r'%-')
        ]
        sp = StatementParser(statement_rules)
        l_w, l_s = sp.process_line(input_mes)
        assert l_w == ["KERNEL", "4", "EVENT", "7", "host", "h1-i2.example.org",
                       "scored", "-0.035", "value", "20.0%"]
