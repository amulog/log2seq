# coding: utf-8

import copy
import datetime
import re
from abc import ABC, abstractmethod

from . import _common

_KEY_TIMESTAMP = _common.KEY_TIMESTAMP
_KEY_STATEMENT = _common.KEY_STATEMENT

# keys for internal processing
_KEY_DATE = "date"
_KEY_TIME = "time"
_KEY_YEAR = "year"
_KEY_MONTH = "month"
_KEY_DAY = "day"
_KEY_HOUR = "hour"
_KEY_MINUTE = "minute"
_KEY_SECOND = "second"
_KEY_MICROSECOND = "microsecond"
_KEY_TZ = "tz"


class _HeaderParserBase(ABC):
    _date_keys = ["year", "month", "day"]
    _time_keys = ["hour", "minute", "second", "microsecond", "tzinfo"]

    def __init__(self, defaults: dict = None,
                 reformat_timestamp: bool = True,
                 astimezone: datetime.tzinfo = None):

        self._defaults = defaults if defaults is not None else dict()
        self._reformat = reformat_timestamp
        self._astz = astimezone

    def _reformat_timestamp(self, ret):

        def _missing_key(k):
            msg = ("{0} is missing; "
                   "use option defaults to add it manually")
            msg = msg.format(k)
            raise _common.LogParseFailure(msg)

        if _KEY_TIMESTAMP in ret:
            dt = ret[_KEY_TIMESTAMP]
        else:
            if _KEY_DATE in ret:
                dateobj = ret.pop(_KEY_DATE)
            else:
                for key in self._date_keys:
                    if key not in ret or ret[key] is None:
                        _missing_key(key)

                args = [ret.pop(key) for key in self._date_keys]
                dateobj = datetime.date(*args)

            if _KEY_TIME in ret:
                timeobj = ret.pop(_KEY_TIME)
            else:
                kwargs = {}
                for key in self._time_keys:
                    if key in ret:
                        kwargs[key] = ret.pop(key)
                timeobj = datetime.time(**kwargs)

            dt = datetime.datetime.combine(dateobj, timeobj)

        # as_timezone option
        if self._astz is not None:
            dt = dt.astimezone(self._astz)

        ret[_KEY_TIMESTAMP] = dt
        return ret

    @abstractmethod
    def process_line(self, line):
        raise NotImplementedError


class HeaderParser(_HeaderParserBase):
    """Parser for header parts in log messages.

    Header parts in log messages provides some items of meta-information.
    For example, default syslogd records messages with timestamps
    and hostnames as header information.
    The other parts (free-format statements) are parsed as statement part
    (with item :class:`Statement`).

    A HeaderParser rule is represented with a list of :class:`Item`.
    Item is a component of regular expression patterns
    to parse corresponding variable item.
    HeaderParser automatically generates one regular expression pattern
    from the items, and tests that it matches the input log messages.
    If matched, HeaderParser extracts variables for the items.

    In HeaderParser rule, one :class:`Statement` item is mandatory.

    If you want to extract timestamp in datetime.datetime format
    (i.e., using reformat_timestamp option),
    the items should include ones with special value names (see :attr:`~Item.value_name`):

    * year (int)
    * month (int)
    * day (int)
    * hour (int, optional)
    * minute (int, optional)
    * second (int, optional)
    * microsecond (int, optional)
    * tzinfo (datetime.tzinfo, optional)

    Besides, you can also use aggregated items with following value names:

    * datetime (datetime.datetime): all
    * date (datetime.date): year, month, day
    * time (datetime.time): hour, minute, second, microsecond, tzinfo

    If some timestamp-related items are not given, please add corresponding values
    (in the specified type) in defaults.
    Note that "year" is missing in some logging framework
    (e.g., default syslogd configuration).

    There are two options to define the placement of Items.
    One is "separator", which is an easier (and recommended) option.
    Separator defines separator characters between Items.
    The other is "full_format",
    which is similar to log_format in logparser[1].
    It is a regular expression holed with Item replacers.
    For example, if full_format is r"<0> <1> <2> \\[<3>\\] <4>",
    <0> will be replaced with the first :class:`Item` in items
    (The number corrsponds to the index of given items).
    If you need "<" and ">", escape it with a backslash.
    The number of replacers must be equal to the length of items.
    Note that optional Items must be manually enclosed with "(" and ")?"
    in the full_format regular expression.
    (e.g., r"<0> <1> <2> (\\[<3>\\] )?<4>" where Item-3 is optional.)

    Args:
        items (list of :class:`Item`): header format rule.
        separator (str, optional): Separators for header part.
            Defaults to white spaces.
        full_format (str, optional): Place format of header part.
            If given, argument separator is ignored.
        defaults (dict, optional): Default values, used for
            missing values (for optional or missing items) in log messages.
        reformat_timestamp (bool, optional): Transform time-related
            items into a timestamp in datetime.datetime object.
            Set false if log messages do not have timestamps.
        astimezone (datetime.tzinfo, optional): Convert timestamp to
            given new timezone by calling datetime.datetime.astimezone().
            Effective only when reformat_timestamp is True.

    Reference:
        [1] logparser: https://github.com/logpai/logparser

    """
    _STATEMENT_FOOTER = r'(?P<' + _KEY_STATEMENT + '>.*)'

    def __init__(self, items, separator=None, full_format=None, **kwargs):
        super().__init__(**kwargs)
        self._l_item = items

        self._items_to_pick = self._get_items_to_pick(items)
        self._optional_check(items)
        self._statement_check(items)
        self._duplication_check(self._items_to_pick)

        if full_format:
            restr = self.make_pattern_full_format(items, full_format)
        else:
            restr = self.make_pattern_separator(items, separator)
        self._reobj = re.compile(restr)

    @property
    def pattern(self):
        return self._reobj

    @classmethod
    def _get_items_to_pick(cls, items):
        items_to_pick = []
        for item in items:
            if isinstance(item, ItemGroup):
                items_to_pick += cls._get_items_to_pick(item.members())
            elif item.dummy:
                pass
            else:
                items_to_pick.append(item)
        return items_to_pick

    @staticmethod
    def _optional_check(items):
        mandatory_items = [item for item in items if item.optional is False]
        if len(mandatory_items) == 0:
            msg = "more than one Item (usually Statement) need to be non-optional"
            raise _common.ParserDefinitionError(msg)

    @staticmethod
    def _statement_check(items):
        names = [item.value_name for item in items]
        if _KEY_STATEMENT not in names:
            msg = "one Statement Item is mandatory in header rules"
            raise _common.ParserDefinitionError(msg)

    @staticmethod
    def _duplication_check(items_to_pick):
        names = [item.match_name for item in items_to_pick]
        if len(names) > len(set(names)):
            print(items_to_pick)
            msg = "Given items include duplicated match names"
            raise _common.ParserDefinitionError(msg)

    @classmethod
    def make_pattern_separator(cls, items, separator):
        return '^' + cls.make_regex_separator(items, separator) + '$'

    @staticmethod
    def make_regex_separator(items, separator):

        def _optional_pattern(pattern):
            return r'(' + pattern + r')?'

        if separator is None:
            sep = r'\s+'
        else:
            sep = r'[' + re.escape(separator) + r']+'
        sep_opt = _optional_pattern(sep)

        ind_first_mandatory_item = [ind for ind, item in enumerate(items)
                                    if item.optional is False][0]
        l_item_patterns = []
        for ind, item in enumerate(items):
            tmp_pattern = item.get_regex()
            # add separator based on the item index
            if ind < ind_first_mandatory_item:
                # left of every mandatory item:
                # add separator to the right of the item
                tmp_pattern = tmp_pattern + sep
            elif ind == ind_first_mandatory_item:
                # first mandatory item: no separator
                # (turning point of the rule to add separators)
                pass
            else:
                # otherwise: add separator to the left of the item
                tmp_pattern = sep + tmp_pattern
            # enclose item pattern and separator as optional part
            if item.optional:
                tmp_pattern = _optional_pattern(tmp_pattern)
            l_item_patterns.append(tmp_pattern)

        # optional separators in line head and tail
        l_item_patterns = [sep_opt] + l_item_patterns + [sep_opt]
        return "".join(l_item_patterns)

    @staticmethod
    def make_pattern_full_format(items, full_format):
        tmp_format = re.sub(" +", r"\\s+", full_format)
        for i, item in reversed(list(enumerate(items))):
            replacer = "<" + str(i) + ">"
            item_regex = item.get_regex()
            if replacer not in tmp_format:
                msg = ("Invalid full_format pattern: "
                       "no replacer {0}".format(replacer))
                raise _common.ParserDefinitionError(msg)
            tmp_format = tmp_format.replace(replacer, item_regex, 1)

        return '^' + tmp_format + '$'

    def process_line(self, line):
        """Parse header part of a log message (i.e., a line).

        Args:
            line (str): A log message without line feed code.

        Returns:
            dict: Parsed items.
        """
        d_items = copy.copy(self._defaults)
        mo = self._reobj.match(line)
        if mo is None:
            return None
        else:
            for item in self._items_to_pick:
                if not item.dummy:
                    tmp = item.pick(mo)
                    if tmp is not None:
                        key, val = tmp
                        d_items[key] = val
            if self._reformat:
                d_items = self._reformat_timestamp(d_items)
            return d_items


# class FormattedHeaderParser(HeaderParser):
#    pass


class Item(ABC):
    """Base class of items, components of header parts.

    Args:
        optional (bool, optional): This item is optional.
            Not all inputs need this item in their header parts.
            If true, Item.pick() returns None if no corresponding part found.
        dummy (bool, optional): Dummy items do not extract any values.
            If true, log2seq does not try extracting a value for this item,
            and Item.pick() will not be called for this item.
            For example, if a header part have multiple same value
            (e.g., year in top and middle), one of them should be dummy
            for avoiding re groupname duplication.
    """
    _match_name = "variable"
    _value_name = "variable"

    def __init__(self, optional=False, dummy=False):
        self._optional = optional
        self._dummy = dummy

    @property
    @abstractmethod
    def pattern(self):
        """str: Get regular expression pattern string for this *Item class*."""
        raise NotImplementedError

    @property
    def optional(self):
        return self._optional

    @property
    def dummy(self):
        return self._dummy

    @property
    def match_name(self):
        """str: Match name of this Item.

        Match name is used to distinguish the extracted values
        in `re <https://docs.python.org/ja/3/library/re.html>`_
        MatchObject.
        Match name cannot be duplicated in a set of ParserHeader items.
        """
        return self._match_name

    @property
    def value_name(self):
        """str: Value name of this :class:`Item`.

        Value name is used as the keys of return value of :class:`HeaderParser`.
        Also, timestamps are reformatted with specific value names.
        """
        return self._value_name

    def test(self, string):
        """Test this Item will match the input string or not.
        Note that this function is only for debugging your parser script
        (because it generates internal re.Pattern for every call).

        Args:
            string: Input string to test matching.

        Returns:
            re.Match or None
        """
        pattern = re.compile(r'^' + self.get_regex() + r'$')
        return pattern.match(string)

    def get_regex(self):
        """Get regular expression pattern string of this :class:`Item` instance.
        """
        if self._dummy:
            return self.pattern
        else:
            return r'(?P<' + self.match_name + r'>' + self.pattern + ')'

    def pick(self, mo):
        """Get value name and the extracted values
        from `re <https://docs.python.org/ja/3/library/re.html>`_
        MatchObject in appropriate format.

        Args:
            mo: MatchObject for combined pattern of :class:`HeaderParser`.

        Returns:
            tuple: :attr:`~Item.value_name` and the value
            extracted by :meth:`Item.pick_value`.
        """
        try:
            return self.value_name, self.pick_value(mo)
        except TypeError:
            # case if mo[self.match_name] is None: optional item
            if self.optional:
                return None
            msg = ("Unoptional item failed to get the corresponding value. "
                   "Don't use special characters such as ? in Item.pattern. "
                   "If using full_format, enclose optional Item with \"()?\" manually.")
            raise _common.ParserDefinitionError(msg)

    def pick_value(self, mo):
        """Get a value from `re <https://docs.python.org/ja/3/library/re.html>`_
        MatchObject in appropriate format.

        Args:
            mo: MatchObject for combined pattern of :class:`HeaderParser`.

        Returns:
            Extracted value for this :class:`Item`. Any type, depending on the class.
            If not specified, a matched string value is returned as is.
        """
        try:
            return mo[self.match_name]
        except IndexError:
            raise IndexError("no match_name {0}".format(self.match_name))


class ItemGroup(Item):
    """ItemGroup enables us a hierarchical parsing of Items.
    One typical use is defining an optional part including multiple Items appearing together.
    Another use is using different separator definition in the ItemGroup part.
    """

    def __init__(self, items, separator=None, optional=False):
        super().__init__(optional=optional, dummy=True)
        self._items = items
        self._pattern = HeaderParser.make_regex_separator(items, separator)

    @property
    def pattern(self):
        return self._pattern

    def members(self):
        return self._items


class Statement(Item):
    """Item for statement part.
    Usually it includes strings except all other items with greedy match.
    """
    _match_name = _KEY_STATEMENT
    _value_name = _KEY_STATEMENT

    @property
    def pattern(self):
        return r'.*'


class YearWithoutCentury(Item):
    """Item for year without century.
    Digits with 2 characters will match
    (e.g., :samp:`21` for year 2021)
    """
    _match_name = "year_nocentury"
    _value_name = "year"

    @property
    def pattern(self):
        return r'[0-9]{2}'

    def pick_value(self, mo):
        """Returns year (including century) in digit format (integer)."""
        century = datetime.datetime.now().year // 100
        return century * 100 + int(mo[self.match_name])


class MonthAbbreviation(Item):
    """Item for abbreviated month names.
    Strings with first capitalized 3 characters will match
    (e.g., :samp:`Jan`, :samp:`Feb`, :samp:`Mar`, ...).
    """
    _match_name = "month_abb"
    _value_name = "month"
    month_name = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

    @property
    def pattern(self):
        return r'|'.join(self.month_name)

    def pick_value(self, mo):
        """Returns month in digit format (integer)."""
        return self.month_name.index(mo[self.match_name]) + 1


class DatetimeISOFormat(Item):
    """Item for datetime in ISO8601 (or RFC3339) format.
    Datetime information (year, month, day, hour minute, second)
    are always included.
    Microseconds and timezone are optionally extracted.

    | e.g., :samp:`2112-09-03T11:22:33`

    | e.g., :samp:`2112-09-03T11:22:33.012345+09:00`
    """
    _match_name = "iso_datetime"
    _value_name = _KEY_TIMESTAMP

    @property
    def pattern(self):
        return (r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T'  # year-month-dayT
                r'(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})'  # hour:minute:second
                r'(\.(?P<dsecond>\d+))?'  # decimal part of seconds
                r'(?P<tz>Z|([+-](\d{2})\:(\d{2})))?')  # timezone

    def pick_value(self, mo):
        """Returns :obj:`datetime.datetime`."""
        # dateutil too slow!
        # return dateutil.parser.parse(mo[self.match_name])

        return self.parse_datetimestr(mo)

    @staticmethod
    def parse_datetimestr(mo):
        # datestr, _, timestr = string.partition("T")
        date = Date.parse_datestr(mo)
        time = Time.parse_timestr(mo)
        return datetime.datetime.combine(date, time)


class Date(Item):
    """Item for date, including year, month, and day.
    Represented in eight-letter numeric string separated with two hyphens.
    Similar to the formar part of DatetimeISOFormat.

    | e.g., :samp:`2112-09-03`
    """
    _match_name = "date"
    _value_name = _KEY_DATE

    @property
    def pattern(self):
        return r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'  # year-month-day

    def pick_value(self, mo):
        """Returns :obj:`datetime.date`."""
        # dateutil too slow!
        # dt = dateutil.parser.parse(mo[self.match_name])
        # return dt.date()

        return self.parse_datestr(mo)

    @staticmethod
    def parse_datestr(mo):
        d = {"year": int(mo.group(_KEY_YEAR)),
             "month": int(mo.group(_KEY_MONTH)),
             "day": int(mo.group(_KEY_DAY))}
        return datetime.date(**d)


class Time(Item):
    """Item for time, including hour, minute, and second.
    It can also include microsecond and timezone, as like :class:`DatetimeISOFormat`.

    | e.g., :samp:`11:22:33`
    """
    _match_name = "iso_time"
    _value_name = _KEY_TIME
    _key_demical_second = "dsecond"

    @property
    def pattern(self):
        return (r'(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})'  # hour:minute:second
                r'(\.(?P<dsecond>\d+))?'  # decimal part of seconds
                r'(?P<tz>Z|([+-](\d{2})\:(\d{2})))?')  # timezone

    def pick_value(self, mo):
        """Returns `datetime.time <https://docs.python.org/ja/3/library/datetime.html>`_."""
        # dateutil too slow!
        # dt = dateutil.parser.parse(mo[self.match_name])
        # return dt.time()

        # manual parse
        return self.parse_timestr(mo)

    @classmethod
    def parse_timestr(cls, mo):
        d = {"hour": int(mo.group(_KEY_HOUR)),
             "minute": int(mo.group(_KEY_MINUTE)),
             "second": int(mo.group(_KEY_SECOND))}
        try:
            if mo.group(cls._key_demical_second) is not None:
                size = len(mo.group(cls._key_demical_second))
                decimal = int(mo.group(cls._key_demical_second))
                microsec = decimal / (10 ** size) * 10 ** 6
                d["microsecond"] = int(microsec)
        except IndexError:
            pass
        try:
            if mo.group(_KEY_TZ) is not None:
                d["tzinfo"] = Time.parse_tz(mo.group(_KEY_TZ))
        except IndexError:
            pass

        return datetime.time(**d)

    @staticmethod
    def parse_tz(string):
        if string == "Z":
            return datetime.timezone.utc

        # referring official _strptime.py (v3.7.2)
        z = string.lower()
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
        tzdelta = datetime.timedelta(seconds=gmtoff,
                                     microseconds=gmtoff_fraction)
        return datetime.timezone(tzdelta)


class DemicalSecond(Item):
    """Item for demical seconds.

    | e.g., :samp:`678` as milliseconds

    | e.g., :samp:`123456` as microseconds
    """
    _match_name = "iso_time"
    _value_name = _KEY_MICROSECOND

    @property
    def pattern(self):
        return r'[0-9]+'

    def pick_value(self, mo):
        string = mo[self.match_name]
        size = len(string)
        decimal = int(string)
        microsec = decimal / (10 ** size) * 10 ** 6
        return int(microsec)


class TimeZone(Item):
    """Item for timezone.

    | e.g., :samp:`+0900`
    """
    _match_name = "timezone"
    _value_name = _KEY_TZ

    @property
    def pattern(self):
        return r'(?P<tz>Z|([+-](\d{2})(\:)?(\d{2})))'  # timezone

    def pick_value(self, mo):
        return self.parse_tz(mo.group(_KEY_TZ))

    @staticmethod
    def parse_tz(string):
        # referring official _strptime.py (v3.7.2)
        z = string.lower()
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
        tzdelta = datetime.timedelta(seconds=gmtoff,
                                     microseconds=gmtoff_fraction)
        return datetime.timezone(tzdelta)


class UnixTime(Item):
    """Item for unixtime integer.

    | e.g., :samp:`1551024123` for 2019-02-25 01:02:03
    """
    _match_name = "unixtime"
    _value_name = _KEY_TIMESTAMP

    @property
    def pattern(self):
        return r'[0-9]+'

    def pick_value(self, mo):
        return datetime.datetime.fromtimestamp(int(mo.group(self._match_name)))


class DateConcat(Item):
    """Item for date without separators.

    | e.g., :samp:`20190225` for 2019-02-25

    | e.g., :samp:`190225` for 2019-02-25 (no_century is True)

    Args:
        no_century (bool, optional): If true, abbreviate year by removing century.
    """
    _match_name = "date_concat"
    _value_name = _KEY_DATE

    def __init__(self, no_century=False, **kwargs):
        super().__init__(**kwargs)
        self._no_century = no_century

        if no_century:
            self._pattern = r'[0-9]{6}'
        else:
            self._pattern = r'[0-9]{8}'

    @property
    def pattern(self):
        return self._pattern

    def pick_value(self, mo):
        string = mo[self.match_name]
        if self._no_century:
            century = datetime.datetime.now().year // 100
            year = century * 100 + int(string[0:2])
            d = {"year": year,
                 "month": int(string[2:4]),
                 "day": int(string[4:6])}
        else:
            d = {"year": int(string[0:4]),
                 "month": int(string[4:6]),
                 "day": int(string[6:8])}
        return datetime.date(**d)


class TimeConcat(Item):
    """Item for time without separators.

    | e.g., :samp:`010203` for 01:02:03
    """
    _match_name = "time_concat"
    _value_name = _KEY_TIME

    @property
    def pattern(self):
        return r'[0-9]{6}'

    def pick_value(self, mo):
        string = mo[self.match_name]
        d = {"hour": int(string[0:2]),
             "minute": int(string[2:4]),
             "second": int(string[4:6])}
        return datetime.time(**d)


class NamedItem(Item, ABC):
    """A base class of namable items.
    Namable items requires an argument for the name.
    The name is used as match name and value name.
    The name should not be duplicated with match names of other items
    (including unnamable items) in one :class:`HeaderParser` rule.

    Args:
        name (string): name of :class:`Item` instance,
            used as match name and value name.
    """

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self._name = name

    @property
    def match_name(self):
        return self._name

    @property
    def value_name(self):
        return self._name


class Digit(NamedItem):
    """:class:`NamedItem` for a digit value."""
    pattern = r'\d+'

    def pick_value(self, mo):
        """Returns integer."""
        return int(mo[self._name])


class String(NamedItem):
    """:class:`NamedItem` for a string.

    The string can include digit and alphabet (no symbol strings in default).
    If you want to allow some additional symbol strings,
    specify it to symbol argument.

    Args:
        symbols (str, optional)
    """

    def __init__(self, name, symbols=None, **kwargs):
        super().__init__(name, **kwargs)

        if symbols is not None:
            if "-" in symbols:
                symbols = symbols.replace("-", "") + "-"
            self._pattern = r'[a-zA-Z0-9' + symbols + r']+'
        else:
            self._pattern = r'[a-zA-Z0-9]+'

    @property
    def pattern(self):
        return self._pattern


class Hostname(NamedItem):
    """:class:`NamedItem` for a hostname (or IPaddress) string.

    Check Hostname.pattern to see the accepted names.
    If your hostname does not match the pattern,
    consider using UserItem.
    (This is because hostname can include various values
    depending on the devices or OSes.)
    """
    pattern = (r'([a-zA-Z0-9:][a-zA-Z0-9:._-]*[a-zA-Z0-9]+)'  # len >= 2
               r'|([a-zA-Z0-9])')  # len == 1


class UserItem(NamedItem):
    """Customizable :class:`NamedItem`.

    The pattern is described in Python Regular Expression Syntax
    (`re <https://docs.python.org/ja/3/library/re.html>`_).
    Some special characters are not allowed to use for this Item
    because HeaderParser generates a single re.Pattern
    by automatically combining the given set of items.

    * Optional parts, such as :regexp:`?`
    * :regexp:`^` and :regexp:`$`

    Args:
        name: same as NamedItem.
        pattern: regular expression pattern of this Item instance.
        strip (str, optional): specified characters will be stripped
            with str.strip() in the parsed object.
    """

    def __init__(self, name, pattern, strip=None, **kwargs):
        super().__init__(name, **kwargs)
        self._pattern = pattern
        self._strip = strip

    @property
    def pattern(self):
        return self._pattern

    def pick_value(self, mo):
        try:
            if self._strip is None:
                return mo[self.match_name]
            else:
                return mo[self.match_name].strip(self._strip)
        except IndexError:
            raise IndexError("no match_name {0}".format(self.match_name))
