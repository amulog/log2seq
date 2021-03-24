# coding: utf-8

import re
from abc import ABC, abstractmethod
import ipaddress

from . import _common

_KEY_STATEMENT = _common.KEY_STATEMENT

# flags for internal process
_FLAG_UNKNOWN = 0
_FLAG_FIXED = 1
_FLAG_SEPARATORS = 2


class StatementParser:
    """Parser for statement parts in log messages.

    Statement parts in log messages describe the event in free-format text.
    This parser will segment the text into words and theire separators.
    The words are parsed as 'words' item, and the separators are
    parsed as 'symbols' item.

    The behavior of this parser is defined with a list of actions.
    The actions are sequentially applied into the statement,
    and separate it into a sequence of words (and separator symbols).

    Args:
        actions (list of any action): Segmentation rules.
            The rules are sequentially applied to the input statement.
    """

    def __init__(self, actions):
        self._l_act = actions

    @staticmethod
    def _verbose(act, input_parts):
        act_name = act.__class__.__name__
        words = []
        for part, flag in input_parts:
            if flag == _FLAG_FIXED:
                words.append("#" + part + "#")
            elif flag == _FLAG_UNKNOWN:
                words.append("'" + part + "'")
            else:
                pass
        print("{0}: {1}".format(act_name, ", ".join(words)))

    @staticmethod
    def _separate(iterable_parts):
        l_w = []
        l_s = []
        prev_isword = True
        for part, flag in iterable_parts:
            current_isword = flag in (_FLAG_FIXED, _FLAG_UNKNOWN)
            if current_isword:
                if part == "":
                    # empty word: remove
                    pass
                elif prev_isword:
                    # separator is missing: add empty separator
                    l_s.append("")
                    l_w.append(part)
                else:
                    l_w.append(part)
            else:
                if prev_isword:
                    l_s.append(part)
                else:
                    # continuous separator: merge into 1 separator
                    l_s[-1] = l_s[-1] + part
            prev_isword = current_isword
        else:
            if prev_isword:
                l_s.append("")

        assert len(l_s) == len(l_w) + 1
        return l_w, l_s

    def process_line(self, statement: str, verbose: bool = False):
        """Parse statement part of a log message (i.e., a line).

        Args:
            statement (string): String of statement part.
            verbose (bool, optional): Show intermediate progress
                of applying actions.

        Returns:
            tuple: List of two components: words and symbols.
            First component, words, is list of words.
            Second component, symbols, is list of separator string symbols.
            The length of symbols is always len(words)+1, which includes
            one before first word and one after last word.
            Some of the symbols can be empty string.
        """
        if verbose:
            print("Statement: {0}".format(statement))
        iterable_parts = [(statement, _FLAG_UNKNOWN), ]

        for act in self._l_act:
            iterable_parts = act.do(iterable_parts)
            if verbose:
                iterable_parts = list(iterable_parts)
                self._verbose(act, iterable_parts)
        return self._separate(iterable_parts)


class _ActionBase(ABC):

    @abstractmethod
    def do(self, input_parts):
        raise NotImplementedError

    @staticmethod
    def _is_active_part(s, flag):
        # UNKNOWN -> true (to be processed)
        # FIXED or SEPARATOR -> false (as is)
        return len(s) > 0 and flag == _FLAG_UNKNOWN

    @staticmethod
    def _standard_patterns(patterns):
        if isinstance(patterns, str):
            return [re.compile(patterns)]
        else:
            return [re.compile(p) for p in patterns]

    @staticmethod
    def _separate_multiple_match(part, iterable_mo, label_match, label_other):
        current = 0
        length = len(part)
        for mo in iterable_mo:
            if mo.start() > current:
                yield part[current:mo.start()], label_other
            yield part[mo.start():mo.end()], label_match
            current = mo.end()
        else:
            if current < length:
                yield part[current:length], label_other

    @staticmethod
    def _separate_partial_match(part, mo, match_groups, label_match, label_other):
        current = 0
        length = len(part)
        sorted_match_groups = sorted(match_groups, key=lambda x: mo.start(x))
        for match_group in sorted_match_groups:
            if mo.start(match_group) == -1:
                continue
            if mo.start(match_group) > current:
                yield part[current:mo.start(match_group)], label_other
            yield part[mo.start(match_group):mo.end(match_group)], label_match
            current = mo.end(match_group)
        else:
            if current < length:
                yield part[current:length], label_other


class Fix(_ActionBase):
    """Add Fixed flag to matched parts.

    Fixed parts will not be segmented by following actions.
    Fixed parts are selected by regular expression of given pattern
    (see `re <https://docs.python.org/ja/3/library/re.html>`_).

    Example:
        >>> p = StatementParser([Split(" "), Fix(r".+\\.txt"), Split(".")])
        >>> p.process_line("parsing sample.txt done.")
        (['parsing', 'sample.txt', 'done'], ['', ' ', ' ', '.'])

    Args:
        patterns (str or list of str):
            Regular expression patterns.
            If multiple patterns are given, they are matched
            with every word in order.
    """

    def __init__(self, patterns):
        self._init_patterns(patterns)

    def _init_patterns(self, patterns):
        self._l_regex = self._standard_patterns(patterns)

    def _test_match_pattern(self, s):
        for reobj in self._l_regex:
            m = reobj.match(s)
            if m:
                return True
        else:
            return False

    def do(self, iterable_parts):
        """Apply this action to every part.
        Matched parts will be fixed.
        This function works as like a filter of the statement.

        Args:
            iterable_parts (iterator of tuple): Sequence of tuples,
                including segmented statement and its annotation label.

        Yields:
            tuple: same format as the input arguments.
        """
        for s, flag in iterable_parts:
            if not self._is_active_part(s, flag):
                yield s, flag
            elif self._test_match_pattern(s):
                yield s, _FLAG_FIXED
            else:
                yield s, flag


class _PartialActionBase(_ActionBase, ABC):

    # private attributes for child classes
    _l_regex = None
    _rest_flag = None
    _fix_groups = None

    def __init__(self, patterns):
        self._init_patterns(patterns)

    @abstractmethod
    def _init_patterns(self, patterns):
        raise NotImplementedError

    @abstractmethod
    def _separate_partial(self, part, mo):
        raise NotImplementedError

    def do(self, iterable_parts):
        for s, flag in iterable_parts:
            if self._is_active_part(s, flag):
                for reobj in self._l_regex:
                    mo = reobj.match(s)
                    if mo:
                        # match -> separate matched part and others
                        for p in self._separate_partial(s, mo):
                            yield p
                        # other patterns are ignored for this part
                        break
                else:
                    yield s, flag
            else:
                yield s, flag


class FixPartial(_PartialActionBase):
    """Extended Fix action to accept complicated patterns.

    Usual :class:`Fix` consider the matched part as a word, and fix it.
    In contrast, :class:`FixPartial` allow the matched part
    to include multiple fixed words or separators.

    Usecase 1:
        | e.g., :samp:`source 192.0.2.1.80 initialized.`

        If you intend to consider :samp:`192.0.2.1.80` as a combination
        of two different word: IPv4 address :samp:`192.0.2.1` and port number :samp:`80`,
        this cannot be segmented with simple Fix and Split actions.
        Following example with :class:`FixPartial` can fix these two variables.

    Example:
        >>> pattern = r'^(?P<ipaddr>(\\d{1,3}\\.){3}\\d{1,3})\\.(?P<port>\\d{1,5})$'
        >>> parser = StatementParser([Split(" "), FixPartial(pattern, fix_groups=["ipaddr", "port"]), Split(".")])
        >>> parser.process_line("source 192.0.2.1.80 initialized.")
        (['source', '192.0.2.1', '80', 'initialized'], ['', '', '.', '', '.'])

    Usecase 2:
        | e.g., :samp:`comment added: "This is a comment description".`

        If you intend to consider the comment (strings between parenthesis)
        as a word without segmentation,
        this cannot be achieved with with simple Fix and Split actions.
        Following example with :class:`FixPartial` can fix the comment part.

    Example:
        >>> pattern = r'^.*?"(?P<fix>.+?)".*$'
        >>> parser = StatementParser([FixPartial(pattern, fix_groups=["fix"], rest_remove=False), Split(' :."')])
        >>> parser.process_line('comment added: "This is a comment description".')
        (['comment', 'added', 'This is a comment description'], ['', ' ', ': "', '".'])

    Args:
        patterns (str): Regular expression patterns.
            If multiple patterns given, the first matched pattern
            is used to Fix the part (other patterns are ignored).
        fix_groups (str or list of str): Name groups in the patterns to fix.
            e.g., ["ipaddr", "port"] for Usecase 1.
            Unspecified groups are not fixed,
            so you can use other group names to other re functions
            like back references.
        rest_remove (bool, optional): This option determines
            how to handle strings outside the fixed groups.
            e.g., 'comment added: "' and '".' in Usecase 2.
            Defaults to False, which means they are left as parts
            for further actions.
            In contrast if True, they are considered eparators
            and will not be segmented further.
    """

    def __init__(self, patterns, fix_groups, rest_remove=False):
        super().__init__(patterns)

        if isinstance(fix_groups, str):
            self._fix_groups = [fix_groups]
        else:
            self._fix_groups = fix_groups

        if rest_remove:
            self._rest_flag = _FLAG_SEPARATORS
        else:
            self._rest_flag = _FLAG_UNKNOWN

    def _init_patterns(self, patterns):
        self._l_regex = self._standard_patterns(patterns)

    def _separate_partial(self, part, mo):
        return self._separate_partial_match(part, mo, self._fix_groups,
                                            _FLAG_FIXED, self._rest_flag)


class FixParenthesis(_PartialActionBase):
    """Extended FixPartial easily used to fix strings between parenthesis.

    The basic usage is similar to FixPartial, but
    this class is designed especially for parenthesis,
    and the format of patterns is simpler.
    For example, FixParenthesis with pattern :samp:`['"', '"']` work samely as
    FixPartial with pattern :regexp:`r'^.*?"(?P<fix>.+?)".*$'`.

    Each pattern is a 2-length list of left and right parenthesis.
    The left and right pattern can consist of multiple characters,
    such as :samp:`["<!--", "-->"]`.

    Example:
        >>> parser = StatementParser([FixParenthesis(['"', '"']), Split(' .:"')])
        >>> parser.process_line('comment added: "This is a comment description".')
        (['comment', 'added', 'This is a comment description'], ['', ' ', ': "', '".'])

    Note: If a statement has multiple pairs of parenthesis,
    you need to add multiple FixParenthesis action to StatementParser actions.
    This is because FixParenthesis accept only one fix_group
    to extract in the action.
    """
    _key_fix = "fix"
    _rest_flag = _FLAG_UNKNOWN
    _fix_groups = [_key_fix, ]

    def _init_patterns(self, patterns):
        if isinstance(patterns, str):
            self._l_regex = [self._init_named_pattern(patterns)]
        elif len(patterns) == 2 and isinstance(patterns[0], str):
            self._l_regex = [self._init_named_pattern(patterns)]
        else:
            self._l_regex = [self._init_named_pattern(pattern)
                             for pattern in patterns]

    @classmethod
    def _init_named_pattern(cls, parent_pattern):
        # non-greedy match
        assert len(parent_pattern) == 2, "Invalid pattern for FixParenthesis"
        p_left = parent_pattern[0]
        p_right = parent_pattern[1]
        restr = r'^.*?' + re.escape(p_left) + \
                '(?P<' + cls._key_fix + r'>.+?)' + \
                re.escape(p_right) + r'.*$'
        return re.compile(restr)

    def _separate_partial(self, part, mo):
        return self._separate_partial_match(part, mo, self._fix_groups,
                                            _FLAG_FIXED, _FLAG_UNKNOWN)


class FixIP(_ActionBase):
    """Add Fixed flag to parts of IP addresses.

    This class use ipaddress library instead of regular expression.

    Args:
        address: match IP addresses, defaults to True
        network: match IP networks, defaults to True
    """

    def __init__(self, address=True, network=True):
        super().__init__()
        self._test_addr = address
        self._test_net = network

    @staticmethod
    def _is_ipaddr(string, ipaddr=True, ipnet=True):
        # fast check: no digit char, no ipaddr
        # because ipaddress lib is slow
        if "." not in string and ":" not in string:
            return False

        if ipaddr:
            try:
                ipaddress.ip_address(string)
            except ValueError:
                pass
            else:
                return True
        if ipnet and "/" in string:
            try:
                ipaddress.ip_network(string, strict=False)
            except ValueError:
                pass
            else:
                return True
        return False

    def _test_match_pattern(self, s):
        return self._is_ipaddr(s, self._test_addr, self._test_net)

    def do(self, iterable_parts):
        """same as Fix.do"""
        for s, flag in iterable_parts:
            if not self._is_active_part(s, flag):
                # FIXED or SEPARATOR -> as is
                yield s, flag
            elif self._test_match_pattern(s):
                # match -> flag changed to FIXED
                yield s, _FLAG_FIXED
            else:
                # not match -> as is
                yield s, flag


class Remove(_ActionBase):
    """Add Separator flag to matched parts.

    Separator parts will be ignored by following actions.
    Separator parts are selected by regular expression of given pattern
    (see `re <https://docs.python.org/ja/3/library/re.html>`_).

    Args:
        patterns (str or list of str):
            Regular expression patterns.
            If multiple patterns are given, they are matched
            with every word in order.
    """

    def __init__(self, patterns):
        self._init_patterns(patterns)

    def _init_patterns(self, patterns):
        self._l_regex = self._standard_patterns(patterns)

    def _test_match_pattern(self, s):
        for reobj in self._l_regex:
            m = reobj.match(s)
            if m:
                return True
        else:
            return False

    def do(self, iterable_parts):
        """Apply this action to every part.
        Matched parts will be fixed.
        This function works as like a filter of the statement.

        Args:
            iterable_parts (iterator of tuple): Sequence of tuples,
                including segmented statement and its annotation label.

        Yields:
            tuple: same format as the input arguments.
        """
        for s, flag in iterable_parts:
            if not self._is_active_part(s, flag):
                yield s, flag
            elif self._test_match_pattern(s):
                yield s, _FLAG_SEPARATORS
            else:
                yield s, flag


class RemovePartial(_PartialActionBase):
    """Extended Remove action to accept complicated patterns.

    Usual :class:`Remove` consider the matched part as a separator.
    In contrast, :class:`RemovePartial` allow
    partially removing separators from a word.

    Example:
        >>> rpattern = r'^.*([^:](?P<colon>:))$'
        >>> fpattern = r'^\\d{2}:\\d{2}:\\d{2}\\.\\d{3}$'
        >>> rules = [Split(" "), RemovePartial(rpattern, remove_groups=["colon"]), Fix(fpattern), Split(":")]
        >>> parser = StatementParser(rules)
        >>> parser.process_line("2000 Mar 4 12:34:56.789: message: duplicated header")
        (['2000', 'Mar', '4', '12:34:56.789', 'duplicated', 'header'], ['', ' ', ' ', ' ', ': ', ' ', ''])
    """

    def __init__(self, patterns, remove_groups):
        super().__init__(patterns)

        if isinstance(remove_groups, str):
            self._match_groups = [remove_groups]
        else:
            self._match_groups = remove_groups

    def _init_patterns(self, patterns):
        self._l_regex = self._standard_patterns(patterns)

    def _separate_partial(self, part, mo):
        return self._separate_partial_match(part, mo, self._match_groups,
                                            _FLAG_SEPARATORS, _FLAG_UNKNOWN)


class Split(_ActionBase):
    """Split statement (or its parts) by given separators.

    For example, separators of white space and dot translates

    | :samp:`['This is a statement.'] -> ['This', 'is', 'a', 'statement']`

    The removed separators (white space and dot in this case)
    will not be considered in further actions.

    Example:
        >>> parser = StatementParser([Split(" .")])
        >>> parser.process_line("This is a statement.")
        (['This', 'is', 'a', 'statement'], ['', ' ', ' ', ' ', '.'])

    Args:
        separators (str): separator symbol strings.
            If iterable, they are imply joined and used all for segmentation.
            Escape sequence is internally added, so you don't need
            to add it manually.
    """

    def __init__(self, separators):
        if not isinstance(separators, str):
            separators = "".join(separators)
        restr = r'([' + re.escape(separators) + '])+'
        self._regex = re.compile(restr)

    @staticmethod
    def _iter_part(s, iterable_mo):
        current = 0
        length = len(s)
        for mo in iterable_mo:
            if mo.start() > current:
                yield s[current:mo.start()], _FLAG_UNKNOWN
            yield s[mo.start():mo.end()], _FLAG_SEPARATORS
            current = mo.end()
        else:
            if current < length:
                yield s[current:length], _FLAG_UNKNOWN

    def do(self, iterable_parts):
        """Apply this action to all input parts.
        This function works as like a filter of the statement.
        This method function is used by StatementParser.

        Args:
            iterable_parts (iterator of tuple): Sequence of tuples,
                including segmented statement and its annotation label.

        Yields:
            tuple: same format as the input arguments.
        """
        for s, flag in iterable_parts:
            if self._is_active_part(s, flag):
                matchobjs = self._regex.finditer(s)
                for tmp_parts in self._iter_part(s, matchobjs):
                    yield tmp_parts
            else:
                yield s, flag


class ConditionalSplit(Fix, Split):

    def __init__(self, patterns, separators):
        Fix.__init__(self, patterns)
        Split.__init__(self, separators)

    def do(self, iterable_parts):
        for s, flag in iterable_parts:
            if not self._is_active_part(s, flag):
                yield s, flag
            elif self._test_match_pattern(s):
                matchobjs = self._regex.finditer(s)
                for tmp_parts in self._iter_part(s, matchobjs):
                    yield tmp_parts
            else:
                yield s, flag
