# coding: utf-8

import copy
import datetime
import re
from abc import ABC, abstractmethod
import dateutil.parser

from . import _common

_KEY_TIMESTAMP = _common.KEY_TIMESTAMP
_KEY_STATEMENT = _common.KEY_STATEMENT

# keys for internal processing
_KEY_DATE = "date"
_KEY_TIME = "time"


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
    HeaderParser automatically generate one regular expression pattern
    from the items, and test that it matchs with input log messages.
    If matched, HeaderParser extracts variables for the items.

    In HeaderParser rule, one :class:`Statement` item is mandatory.
    Also, if you want to extract timestamp in datetime.datetime format
    (i.e., using reformat_timestamp option),
    the items should includes ones with special value names (see :attr:`~Item.value_name`):

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

    If some of the Items not used, please add the values
    (in the specified type) in defaults.
    Note that "year" is missing in some logging framework
    (e.g., default syslogd configuration).

    Args:
        items (list of :class:`Item`): header format rule.
        separator (str, optional): Separators for header part.
            Defaults to white spaces.
        defaults (dict, optional): Default values, used for
            missing values (for optional or missing items) in log messages.
        reformat_timestamp (bool, optional): Transform time-related
            items into a timestamp in datetime.datetime object.
            Set false if log messages do not have timestamps.
        astimezone (datetime.tzinfo, optional): Convert timestamp to
            given new timezone by calling datetime.datetime.astimezone().
            Effective only when reformat_timestamp is True.
    """
    _STATEMENT_FOOTER = r'(?P<' + _KEY_STATEMENT + '>.*)'

    def __init__(self, items, separator=None, **kwargs):
        super().__init__(**kwargs)
        self._l_item = items
        self._separator = separator

        self._statement_check()
        self._duplication_check()

        self._make_regex()

    def _statement_check(self):
        names = [item.value_name for item in self._l_item]
        if _KEY_STATEMENT not in names:
            msg = "Statement Item is needed"
            raise _common.ParserDefinitionError(msg)

    def _duplication_check(self):
        names = [item.match_name for item in self._l_item
                 if not item.dummy]
        if len(names) > len(set(names)):
            msg = "Given items include duplicated match names"
            raise _common.ParserDefinitionError(msg)

    def _separator_regex(self):
        if self._separator is None:
            return r'\s+'
        else:
            return r'[' + self._separator + ']+'

    def _make_regex(self):
        sep = self._separator_regex()
        l_item_regex = []
        for i, item in enumerate(self._l_item):
            last = (i == len(self._l_item) - 1)
            l_item_regex.append(item.get_regex(separator=sep, last=last))
        restr = r'^' + "".join(l_item_regex) + '$'
        self._reobj = re.compile(restr)

    def process_line(self, line):
        """Parse header part of a log message (i.e., a line).

        Args:
            line (str): A log message without line feed code.

        Returns:
            dict: Parsed items.
        """
        items = copy.copy(self._defaults)
        mo = self._reobj.match(line)
        if mo is None:
            return None
        else:
            for item in self._l_item:
                tmp = item.pick(mo)
                if tmp is not None:
                    key, val = tmp
                    items[key] = val
            if self._reformat:
                items = self._reformat_timestamp(items)
            return items


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
        """str: Get regular expression pattern for this *Item class*
        in string format."""
        raise NotImplementedError

    @property
    def optional(self):
        """bool: This Item instance is optional or not."""
        return self._optional

    @property
    def dummy(self):
        """bool: This Item instance is dummy or not."""
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

    def get_regex(self, separator=r'\s+', last=False):
        """Get regular expression pattern of this :class:`Item` instance
        in string format.
        The pattern is modified considering the options
        for :class:`HeaderParser` and this :class:`Item`.

        Args:
            separator (str, optional): separator regular expression pattern.
            last (bool, optional): True if this Item instance is the last one
                in :class:`HeaderParser` items.

        Returns:
            str: regular expression pattern of this Item instance.
        """
        return self._enclose_regex(self.pattern, separator, last)

    def _enclose_regex(self, core, separator, last):
        if self._dummy:
            restr = core
        else:
            restr = r'(?P<' + self.match_name + r'>' + core + ')'
        if not last:
            restr += separator
        if self._optional:
            restr = r'(' + restr + ')?'
        return restr

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
            msg = ("Unoptional item failed to get the corresponding value. ",
                   "Don't use special characters such as ? in Item.pattern.")
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
        return mo[self.match_name]


class Statement(Item):
    """Item for statement part.
    Usually it includes all strings except header part.
    """
    _match_name = _KEY_STATEMENT
    _value_name = _KEY_STATEMENT

    @property
    def pattern(self):
        return r'.*'


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
        return (r'(\d{4})-(\d{2})-(\d{2})T'  # year-month-dayT
                r'(\d{2}):(\d{2}):(\d{2})'  # hour:minute:second
                r'(\.\d{6})?'  # microseconds
                r'([+-](\d{2})\:(\d{2}))?')  # timezone

    def pick_value(self, mo):
        """Returns :obj:`datetime.datetime`."""
        return dateutil.parser.parse(mo[self.match_name])


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
        return r'(\d{4})-(\d{2})-(\d{2})'  # year-month-day

    def pick_value(self, mo):
        """Returns :obj:`datetime.date`."""
        dt = dateutil.parser.parse(mo[self.match_name])
        return dt.date()


class Time(Item):
    """Item for time, including hour, minute, and second.
    It can also include microsecond and timezone, as like :class:`DatetimeISOFormat`.

    | e.g., :samp:`11:22:33`
    """
    _match_name = "iso_time"
    _value_name = _KEY_TIME

    @property
    def pattern(self):
        return (r'(\d{2}):(\d{2}):(\d{2})'  # hour:minute:second
                r'(\.\d{6})?'  # microseconds
                r'([+-](\d{2})\:(\d{2}))?')  # timezone

    def pick_value(self, mo):
        """Returns `datetime.time <https://docs.python.org/ja/3/library/datetime.html>`_."""
        dt = dateutil.parser.parse(mo[self.match_name])
        return dt.time()


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

    The string can include digit and alphabet, without any symbol strings.
    """
    pattern = r'[0-9A-Za-z]+'


class Hostname(NamedItem):
    """:class:`NamedItem` for a hostname (or IPaddress) string.

    Check Hostname.pattern to see the accepted names.
    If your hostname does not match the pattern,
    consider using UserItem.
    (This is because hostname can include various values
    depending on the devices or OSes.)
    """
    pattern = (r'([a-zA-Z0-9:][a-zA-Z0-9:.-]*[a-zA-Z0-9]+)'  # len >= 2
               r'|([a-zA-Z0-9])')  # len == 1


class UserItem(NamedItem):
    """Customizable :class:`NamedItem`.

    The pattern is described in Python Regular Expression Syntax
    (`re <https://docs.python.org/ja/3/library/re.html>`_).
    Some special characters are not allowed to use for this Item.

    * Optional parts, such as :regexp:`?`
    * :regexp:`^` and :regexp:`$`

    Args:
        name: same as NamedItem.
        pattern: regular expression pattern of this Item instance.
    """

    def __init__(self, name, pattern, **kwargs):
        super().__init__(name, **kwargs)
        self._pattern = pattern

    @property
    def pattern(self):
        return self._pattern
