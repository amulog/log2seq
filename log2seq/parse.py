#!/usr/bin/env python
# coding: utf-8

import re
import datetime
import ipaddress

KEY_FIX = 'fix'


class Parser():

    month_name = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    def __init__(self, rules, default_year = None):
        self._header_rules, self._split_rules = rules
        self.default_year = default_year

    def _set_year(self):
        if self.default_year is None:
            return datetime.datetime.today().year
        else:
            return int(self.default_year)

    @classmethod
    def _str2month(cls, string):
        if not string in cls.month_name:
            return None
        else:
            return cls.month_name.index(string) + 1

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
        #eval header_list
        for reobj in self._header_rules:
            m = reobj.match(line)
            if m is not None:
                d = m.groupdict()
                break
        else:
            raise SyntaxError(
                "Parsing log header failed: {0}".format(line))

        if d['year'] is None:
            year = self._set_year()
        else:
            year = d['year']
        if 'month' in d:
            month = d['month']
        elif 'bmonth' in d:
            month = self._str2month(d['bmonth'])
        else:
            raise SyntaxError("No month or bmonth in header_regex")

        dt = datetime.datetime(year = int(year), month = int(month),
                               day = int(d['day']),
                               hour = int(d['hour']),
                               minute = int(d['minute']),
                               second = int(d['second']),
                               microsecond = 0)
        host = d['host']
        message = d['message']
        return dt, host, message

    def process_message(self, mes):

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
        line = line.rstrip("\n")
        if line == "":
            return None, None, None, None
        dt, host, message = self.process_header(line)
        if message is None or message == "":
            return None, None, None, None
        l_w, l_s = self.process_message(message)
        return dt, host, l_w, l_s


def init_parser(rules = None):
    if rules is None:
        from . import default_script
        rules = (default_script.header_rules, default_script.split_rules)
    return Parser(rules)

