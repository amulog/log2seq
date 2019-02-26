#!/usr/bin/env python
# coding: utf-8

import re
import datetime
import ipaddress

KEY_TIMESTAMP = 'timestamp'
KEY_MESSAGE = 'message'
KEY_WORDS = 'words'
KEY_SYMBOLS = 'symbols'
KEY_FIX = 'fix'


class TimestampParser(object):
    """Parse timestamp in header part of log messages.
    This class generate datetime.datetime by following name groups.
    - year (digit, optional)
    - month (digit or abbreviated month name like "Jan")
    - day (digit)
    - hour (digit)
    - minute (digit)
    - second (digit)
    - microsecond (digit, optional)
    - tz (utc offset (like +0900) or tzname (like UTC), optional)
    """

    month_name = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    numeric_tz = re.compile(r"^[+-]\d{2}:\d{2}(:\d+)?$")

    def __init__(self, defaults):
        self._defaults = defaults

    @classmethod
    def _str2month(cls, string):
        if len(string) == 2:
            return int(string)
        elif len(string) == 3:
            return cls.month_name.index(string) + 1
        else:
            return None

    @classmethod
    def _str2tz(cls, string):
        # referring official _strptime.py (v3.7.2)
        z = string.lower()
        if cls.numeric_tz.match(z):
            if z[3] == ':':
                z = z[:3] + z[4:]
                if len(z) > 5:
                    if z[5] != ':':
                        raise ValueError
                    z = z[:5] + z[6:]
            hours = int(z[1:3])
            minutes = int(z[3:5])
            seconds = int(z[5:7] or 0)
            gmtoff = (hours * 60 * 60) + (minutes * 60) + seconds
            gmtoff_remainder = z[8:]
            gmtoff_remainder_padding = "0" * (6 - len(gmtoff_remainder))
            gmtoff_fraction = int(gmtoff_remainder + gmtoff_remainder_padding)
            if z.startswith("-"):
                gmtoff = -gmtoff
                gmtoff_fraction = -gmtoff_fraction
            tzdelta = datetime_timedelta(seconds = gmtoff,
                                         microseconds = gmtoff_fraction)
            return datetime.timezone(tzdelta)
        else:
            if z in ("utc", "gmt"):
                return datetime.timezone.utc
            else:
                # use local time
                return None

    def parse(self, d):
        """
        Args:
            d (dict): parsed message by LogParser
        
        Returns:
            d (dict): same as d in args, but 
                      added d[KEY_TIMESTAMP] (datetime)"""

        def _get(groupdict, key):
            if not key in groupdict or groupdict[key] is None:
                if key in self._defaults:
                    return self._defaults[key]
                else:
                    return None
            else:
                return groupdict[key]

        kwargs = {k: int(_get(d, k))
                  for k in ('day', 'hour', 'minute', 'second')}

        year = _get(d, 'year')
        if year is None:
            year = datetime.datetime.today().year
        kwargs['year'] = int(year)

        month = _get(d, 'month')
        kwargs['month'] = self._str2month(month)

        ms = _get(d, 'microsecond')
        if ms is not None:
            kwargs['microsecond'] = int(ms)

        tzstr = _get(d, 'tz')
        if tzstr is not None:
            tz = self._str2tz(tzstr)
            if tz is not None: # not local time
                kwargs['tzinfo'] = tz

        try:
            return datetime.datetime(**kwargs)
        except:
            msg = "parsing timestamp failed: {0}".format(kwargs)
            raise SyntaxError(msg)


class LogParser():
    """Parse log messages by 2 external rules:
    header_rules and split_rules.

    * header_rules (list of re.SRE_Pattern)
    Used for parsing log message header (timestamp and hosts)
    Evaluated in order, most top matched boject is used.
    You should specify "message" named group in the regular expression.
    "message" group is used as a message body in split_rules step.

    To parse timestamps as datetime.datetime in header,
    TimestampParser is used in default.
    If some name group not given, values in defaults (dict) is loaded.
    In addition, other values like PRI or hostname can
    also be parsed by named groups.
    
    * split_rules (list of (action, target))
    Used for splitting message into a sequence of words.
    split_rules is a procedure of multiple actions.
    There are 2 kinds of actions: split and fix.
    
    - action split
    The given message is splitted with given regular expression.
    Matched characters are recognized as symbol strings.
    Give capturing group like r"([ ,\.])".
    
    - action fix
    Some words should not be splitted by symbol strings uniformly.
    e.g., ":" is usually a splitter, but ":" in IPv6 addr is not a splitter.
    Action fix avoids such excessive splitting.
    Action fix receives regular expression, and matched string is fixed.
    Fixed word will not be splitted later with action split.
    
    If 'fix' named group is specified, string in the group is fixed
    and the other characters are recognized as symbol strings.
    """

    def __init__(self, rules, defaults = dict(),
                 timestamp_parser = TimestampParser):
        self._header_rules, self._split_rules = rules
        self._tp = timestamp_parser(defaults)

    @staticmethod
    def _is_ip(string, ipaddr = True, ipnet = True):
        if ipaddr:
            try:
                r = ipaddress.ip_address(string)
            except ValueError:
                pass
            else:
                return True

        if ipnet:
            try:
                r = ipaddress.ip_network(string, strict = False)
            except ValueError:
                pass
            else:
                return True

        return False

    def process_header(self, line):
        """Parse header in a log message.
        
        Args:
            line (str): a log line.
            
        Returns:
            d (dict): parsed log message. Basically it is
                      generated as a groupdict of regular expressions.
        """
        #eval header_list
        for reobj in self._header_rules:
            m = reobj.match(line)
            if m is not None:
                d = m.groupdict()
                break
        else:
            msg = "parsing log header failed: {0}".format(line)
            raise SyntaxError(msg)

        d[KEY_TIMESTAMP] = self._tp.parse(d)
        return d

    def process_message(self, mes):
        """Parse a sequence of words and splitting symbols
        in log message body (parsed in process_header).
        
        Args:
            mes (str): a string of message body.
            
        Returns:
            l_w (list[str]): A sequence of words.
            l_s (list[str]): A sequence of splitting symbols.
                             The length is equal to len(l_w) + 1.
                             Some symbol can be empty string.
        """

        def _split_regex(input_seq, input_seq_flag, regexobj):
            ret_seq = []
            ret_seq_flag = []
            for i, (s, flag) in enumerate(zip(input_seq, input_seq_flag)):
                if flag == 0:
                    tmp_seq = regexobj.split(s)
                    tmp_seq_flag = [j % 2 for j, v in enumerate(tmp_seq)]
                    ret_seq += tmp_seq
                    ret_seq_flag += tmp_seq_flag
                else:
                    # pass symbols (1) and fixed words (-1)
                    ret_seq.append(s)
                    ret_seq_flag.append(flag)
            return ret_seq, ret_seq_flag

        def _fix_regex(input_seq, input_seq_flag, list_reobj):
            if not isinstance(list_reobj, list):
                list_reobj = [list_reobj,]
            ret_seq = input_seq[:]
            ret_seq_flag = input_seq_flag[:]
            for i, (s, flag) in enumerate(zip(input_seq, input_seq_flag)):
                if flag == 1:
                    # pass symbols
                    continue
                for reobj in list_reobj:
                    m = reobj.match(s)
                    if m:
                        d = m.groupdict()
                        if KEY_FIX in d:
                            word = m.group(KEY_FIX)
                            before = s[:m.start(KEY_FIX)]
                            end = s[m.end(KEY_FIX):]
                            assert input_seq_flag[i-1] == 1
                            assert input_seq_flag[i+1] == 1
                            ret_seq[i-1] = input_seq[i-1] + before
                            ret_seq[i] = word
                            ret_seq[i+1] = end + input_seq[i+1]
                        ret_seq_flag[i] = -1
            return ret_seq, ret_seq_flag

        def _fix_ip(input_seq, input_seq_flag, test_ipaddr, test_ipnet):
            ret_seq_flag = input_seq_flag[:]
            for i, (s, flag) in enumerate(zip(input_seq, input_seq_flag)):
                if flag == 1:
                    continue
                if self._is_ip(s, test_ipaddr, test_ipnet):
                    ret_seq_flag[i] = -1
            return input_seq, ret_seq_flag

        seq = [mes]
        seq_flag = [0] # 0: word, 1: symbol, -1: fixed word

        # eval split_list
        for action, obj in self._split_rules:
            if action == 'split':
                seq, seq_flag = _split_regex(seq, seq_flag, obj)
            elif action == 'fix':
                seq, seq_flag = _fix_regex(seq, seq_flag, obj)
            elif action == 'fixip':
                test_ipaddr, test_ipnet = obj
                seq, seq_flag = _fix_ip(seq, seq_flag,
                                        test_ipaddr, test_ipnet)
            else:
                raise SyntaxError("action {0} not available".format(action))

        # remove empty words
        empty_index = [i for i, v in enumerate(seq)
                       if len(v) == 0 and seq_flag[i] < 1]
        for i in sorted(empty_index, reverse = True):
            if i == 0 or i == len(seq) - 1:
                seq.pop(i)
                seq_flag.pop(i)
            else:
                before = seq[:i-2+1]
                before_flag = seq_flag[:i-2+1]
                after = seq[i+2:]
                after_flag = seq_flag[i+2:]
                jbefore = seq[i-1]
                jafter = seq[i+1]
                assert seq_flag[i-1] == 1
                assert seq_flag[i+1] == 1
                seq = before + [jbefore + jafter] + after
                seq_flag = before_flag + [1] + after_flag

        # put empty symbol in top and bottom of seq
        if not seq_flag[0] == 1:
            seq = [''] + seq
            seq_flag = [1] + seq_flag
        if not seq_flag[-1] == 1:
            seq = seq + ['']
            seq_flag = seq_flag + [1]

        l_w = [v for v, flag in zip(seq, seq_flag) if flag < 1]
        l_s = [v for v, flag in zip(seq, seq_flag) if flag == 1]
        assert len(l_s) == len(l_w) + 1

        return l_w, l_s

    def process_line(self, line):
        """Parse log message by 2 steps
        (process_header and process_message).
        
        Args:
            line (str): A string of log line.

        Returns:
            d (dict): Parsed log message object with following contents.
            d["timestamp"] (datetime.datetime): Parsed with timestamp_parser
                                                (specified in __init__).
            d["words"] (list [str]): A sequence of words in message body.
            d["symbols"] (list [str]): A sequence of splitting symbols
                                       in message body.
            other contents specified as named groups
            in header_rules is also available. (like d["host"])
        """
        line = line.rstrip("\n")
        if line == "":
            return None
        d = self.process_header(line)
        mes = d[KEY_MESSAGE]
        if mes:
            l_w, l_s = self.process_message(mes)
            d[KEY_WORDS] = l_w
            d[KEY_SYMBOLS] = l_s
        return d


def init_parser(rules = None, defaults = dict()):
    """Returns LogParser object with given arguments.
    If args are omitted, default rules (in default_script.py) are used.

    Args:
        rules: A tuple of header_rules and split rules.
               See LogParser for detailed information.

    Returns:
        Logparser instance
    """
    if rules is None:
        from . import default_script
        rules = (default_script.header_rules, default_script.split_rules)
    return LogParser(rules, defaults)

