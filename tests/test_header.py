import re
import datetime
import unittest


class TestHeader(unittest.TestCase):

    def test_default(self):
        from log2seq.preset import default
        hp = default()

        # syslog-style lines carry no year; default() fills it from the current
        # year, so assert host/message/time components but not the (run-dependent)
        # year.
        ret = hp.process_header("Apr  1 02:23:45 host-name.example.org message here")
        assert ret["host"] == "host-name.example.org"
        assert ret["message"] == "message here"
        ts = ret["timestamp"]
        assert (ts.month, ts.day, ts.hour, ts.minute, ts.second) == (4, 1, 2, 23, 45)

        ret = hp.process_header("Jun 30 11:11:11.012345+09:00 2001:db8::beef something")
        assert ret["host"] == "2001:db8::beef"
        assert ret["message"] == "something"
        ts = ret["timestamp"]
        assert (ts.month, ts.day, ts.hour, ts.minute, ts.second, ts.microsecond) \
            == (6, 30, 11, 11, 11, 12345)
        assert ts.utcoffset() == datetime.timedelta(hours=9)

        ret = hp.process_header("Jul 12 22:22:22-06:00 host something")
        assert ret["host"] == "host"
        assert ret["message"] == "something"
        ts = ret["timestamp"]
        assert (ts.month, ts.day, ts.hour, ts.minute, ts.second) == (7, 12, 22, 22, 22)
        assert ts.utcoffset() == datetime.timedelta(hours=-6)

        # An explicit year makes the whole timestamp deterministic.
        ret = hp.process_header("2020 May  2 22:22:22 192.0.2.1 message there")
        assert ret["host"] == "192.0.2.1"
        assert ret["message"] == "message there"
        assert ret["timestamp"] == datetime.datetime(2020, 5, 2, 22, 22, 22)

        # ISO format (Date + Time) is parsed by the default's second rule.
        ret = hp.process_header("2112-09-03 11:22:33 host something failure")
        assert ret["host"] == "host"
        assert ret["message"] == "something failure"
        assert ret["timestamp"] == datetime.datetime(2112, 9, 3, 11, 22, 33)

        ret = hp.process_header("2112-09-03 01:02:03.987654+09:00 host something")
        assert ret["host"] == "host"
        assert ret["message"] == "something"
        ts = ret["timestamp"]
        assert ts.replace(tzinfo=None) == datetime.datetime(2112, 9, 3, 1, 2, 3, 987654)
        assert ts.utcoffset() == datetime.timedelta(hours=9)

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

    def test_year_without_century(self):
        # The century completion must be deterministic (no datetime.now()
        # dependence). The default prefix is 20 (2000-2099), reproducing the
        # previous now()-based behavior for runs in this century.
        from log2seq import header

        item = header.YearWithoutCentury()
        assert item.pick_value(item.test("21")) == 2021
        assert item.pick_value(item.test("99")) == 2099
        # Explicit override yields a year the old now()-based code could not.
        item19 = header.YearWithoutCentury(century=19)
        assert item19.pick_value(item19.test("21")) == 1921

        # DateConcat(no_century=True) shares the same completion.
        dc = header.DateConcat(no_century=True)
        assert dc.pick_value(dc.test("210905")) == datetime.date(2021, 9, 5)
        dc19 = header.DateConcat(no_century=True, century=19)
        assert dc19.pick_value(dc19.test("210905")) == datetime.date(1921, 9, 5)
        # Full (8-digit) date is unaffected by the century option.
        dc8 = header.DateConcat()
        assert dc8.pick_value(dc8.test("19990905")) == datetime.date(1999, 9, 5)

    def test_timezone(self):
        # Both Time and TimeZone share one tz parser. "Z" used to raise
        # IndexError when parsed via TimeZone; it must now resolve to UTC.
        from log2seq import header

        utc = datetime.timezone.utc
        jst = datetime.timezone(datetime.timedelta(hours=9))
        west = datetime.timezone(datetime.timedelta(hours=-6))

        tz = header.TimeZone()
        assert tz.pick_value(tz.test("Z")) == utc
        assert tz.pick_value(tz.test("+0900")) == jst
        assert tz.pick_value(tz.test("+09:00")) == jst
        assert tz.pick_value(tz.test("-06:00")) == west

        assert header.Time.parse_tz("Z") == utc
        assert header.Time.parse_tz("+0900") == jst
        assert header.Time.parse_tz("-06:00") == west

    def test_microsecond(self):
        # fractional seconds are padded/truncated to 6 digits, integer-only.
        from log2seq import header

        ds = header.DemicalSecond()
        assert ds.pick_value(ds.test("1")) == 100000
        assert ds.pick_value(ds.test("012345")) == 12345
        assert ds.pick_value(ds.test("123456")) == 123456
        assert ds.pick_value(ds.test("1234567")) == 123456  # truncated to 6

        t = header.Time()
        assert t.pick_value(t.test("01:02:03.000001")).microsecond == 1
        assert t.pick_value(t.test("01:02:03.5")).microsecond == 500000

    def test_unixtime(self):
        # default UTC -> machine-independent; an explicit tz is honored.
        from log2seq import header

        ut = header.UnixTime()
        assert ut.pick_value(ut.test("1551024123")) == \
            datetime.datetime(2019, 2, 24, 16, 2, 3,
                              tzinfo=datetime.timezone.utc)
        jst = datetime.timezone(datetime.timedelta(hours=9))
        assert header.UnixTime(tz=jst).pick_value(ut.test("1551024123")) == \
            datetime.datetime(2019, 2, 25, 1, 2, 3, tzinfo=jst)

    def test_separate_timezone_item(self):
        # A standalone TimeZone item coexists with Time (no group-name clash)
        # and its offset is applied to the timestamp (previously dropped).
        from log2seq import header

        rule = [header.Date(), header.Time(), header.TimeZone(),
                header.Hostname("host"), header.Statement()]
        hp = header.HeaderParser(rule, separator=" ")

        jst = datetime.timezone(datetime.timedelta(hours=9))
        r = hp.process_line("2020-05-02 11:22:33 +09:00 host the message")
        assert r["timestamp"] == datetime.datetime(2020, 5, 2, 11, 22, 33,
                                                   tzinfo=jst)
        assert "tz" not in r and "tzinfo" not in r
        assert r["host"] == "host"

        r2 = hp.process_line("2020-05-02 11:22:33 Z host msg")
        assert r2["timestamp"] == datetime.datetime(2020, 5, 2, 11, 22, 33,
                                                    tzinfo=datetime.timezone.utc)

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
