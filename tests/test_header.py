import re
import datetime
import unittest


class TestHeader(unittest.TestCase):

    def test_default(self):
        input_lines = [
            "Apr  1 02:23:45 host-name.example.org message here",
            "2020 May  2 22:22:22 192.0.2.1 message there",
            "Jun 30 11:11:11.012345+09:00 2001:db8::beef something",
            "Jul 12 22:22:22-06:00 host something"
            "2112-09-03 11:22:33 host something failure"
            "2112-09-03 01:02:03.987654+09:00 host something"
        ]

        from log2seq.preset import default
        hp = default()
        for line in input_lines:
            ret = hp.process_header(line)
            assert ret is not None

    def test_full_format(self):
        input_lines = ["Sep  1 01:02:03 host daemon[12345]: test: message ::1",
                       "Sep 12 11:22:33 host doraemon: restart"]

        from log2seq import header
        from log2seq import preset
        from log2seq import LogParser
        header_rule = [header.MonthAbbreviation(),
                       header.Digit("day"),
                       header.Time(),
                       header.Hostname("host"),
                       header.String("function"),
                       header.Digit("pid", optional=True),
                       header.Statement()]
        full_format = r"<0> <1> <2> <3> <4>(\[<5>\])?: <6>"
        defaults = {"year": datetime.datetime.now().year}
        hp = header.HeaderParser(header_rule, full_format=full_format,
                                 defaults=defaults)
        sp = preset.default_statement_parser()
        parser = LogParser(hp, sp)

        for line in input_lines:
            ret = parser.process_header(line)
            assert ret is not None

    def test_time(self):
        input_lines = ["2112-09-03 11:22:33.012345 host something failure"]

        from log2seq.preset import default
        hp = default()
        for line in input_lines:
            ret = hp.process_header(line)
            ts = ret["timestamp"]
            assert ts.date() == datetime.date(2112, 9, 3)
            assert ts.time().hour == 11
            assert ts.time().minute == 22
            assert ts.time().second == 33
            assert ts.time().microsecond == 12345

    def test_items(self):
        from log2seq import header

        # datetime
        regex = re.compile(header.DatetimeISOFormat().pattern)
        assert regex.match("2112-09-03T03:00:00")
        assert regex.match("2112-09-03T03:00:00+09:00")
        assert regex.match("2112-09-03T03:00:00.000000")
        assert regex.match("2112-09-03T03:00:00.000000+09:00")

        # date
        regex = re.compile(header.Date().pattern)
        assert regex.match("2112-09-03") is not None

        # time
        regex = re.compile(header.Time().pattern)
        assert regex.match("12:34:56") is not None
        assert regex.match("12:34:56.012345-03:00") is not None

        # digit
        regex = re.compile(header.Digit("digit").pattern)
        assert regex.match("123456") is not None

        # hostname
        regex = re.compile(header.Hostname("host").pattern)
        assert regex.match("localhost") is not None
        assert regex.match("hostname1") is not None
        assert regex.match("host-name.example.net") is not None
        assert regex.match("192.0.2.1") is not None
        assert regex.match("2001:db8::1") is not None
        assert regex.match("::1") is not None
