#!/usr/bin/env python
# coding: utf-8

"""log2seq loads following 2 objects from this script:
* header_rules (list of re.SRE_Pattern)
* split_rules (list of (action, target))

* header_rules (list of re.SRE_Pattern)
Used for parsing log message header (timestamp and hosts)
Evaluated in order, most top matched boject is used.
You should specify following named group in the regular expression.
- message (str)
This group is used as a message body.

Also, log2seq parses timestamp by following named groups.
- year (digit, optional)
- month (digit or abbreviated month name like "Jan")
- day (digit)
- hour (digit)
- minute (digit)
- second (digit)
- microsecond (digit, optional)
- tz (utc offset (like +0900) or tzname (like UTC))
Usually, you also need to give host (str) named group for further analysis.

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

import re

_restr_timestamp = (r"((?P<year>\d{4})\s+)?"           # %Y_ (optional)
                    r"(?P<month>[a-zA-Z]{3})\s+"       # %m_
                    r"(?P<day>\d{1,2}\s+)"             # %d_
                    r"(?P<hour>\d{2}):"                # %H:
                    r"(?P<minute>\d{2}):"              # %M:
                    r"(?P<second>\d{2})"               # %S
                    r"(\s+(?P<tz>[A-Z]{3,5}))?")       # %Z
_restr_datetime = (r"(?P<year>\d{4})-"                 # %Y-
                   r"(?P<month>\d{2})-"                # %m-
                   r"(?P<day>\d{2})\s+"                # %d_
                   r"(?P<hour>\d{2}):"                 # %H:
                   r"(?P<minute>\d{2}):"               # %M:
                   r"(?P<second>\d{2})"                # %S
                   r"(\.(?P<microsecond>\d{6}))?"      # %f
                   r"((?P<tz>[+-]\d{4}))?"             # %z
                   )
_restr_host = (r"([a-zA-Z0-9][a-zA-Z0-9:.-]*[a-zA-Z0-9]" # len >= 2
               r"|[a-zA-Z0-9])")                         # len == 1
_restr_syslog_ts = (r"^{0}\s+(?P<host>{1})\s*(?P<message>.*)$".format(
    _restr_timestamp, _restr_host))
_restr_syslog_dt = (r"^{0}\s+(?P<host>{1})\s*(?P<message>.*)$".format(
    _restr_datetime, _restr_host))

#_restr_double_quatation = re.compile(r"^\"(?P<fix>[a-zA-Z0-9-]+)\".*$")
_split_regex_first = re.compile(r"([\(\)\[\]\{\}\"\|\+',=><;`# ]+)")
_split_regex_second = re.compile(r"([:]+)")
_restr_time = re.compile(r"^\d{2}:\d{2}:\d{2}(\.\d+)?$")
_restr_mac = re.compile(r"^[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}$")

header_rules = [re.compile(_restr_syslog_ts),
                re.compile(_restr_syslog_dt)]
split_rules = [('split', _split_regex_first),
               ('fixip', (True, True)),
               ('fix', [_restr_time, _restr_mac]),
               ('split', _split_regex_second)]

