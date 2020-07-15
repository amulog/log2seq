# coding: utf-8

import re
from abc import ABC, abstractmethod
import ipaddress
import numpy as np

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
    The words are parsed as 'words' items, and the separators are
    parsed as `symbols`.

    The behavior of this parser is defined with a sequence of actions.
    The actions are sequentially applied into the statement,
    and separate it into a sequence of words (and separator symbols).

    Args:
        actions (list of _ActionBase): Segmentation rules.
            The rules are sequentially applied to the input statement.
    """

    def __init__(self, actions):
        self._l_act = actions + [_Reformat()]

    @staticmethod
    def _separate(input_parts, input_flags):
        l_w = []
        l_s = []
        prev_isword = True
        for i, (part, flag) in enumerate(zip(input_parts, input_flags)):
            current_isword = flag in (_FLAG_FIXED, _FLAG_UNKNOWN)
            if current_isword:
                if prev_isword:
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

    def process_line(self, statement: str):
        """Parse statemtn part of a log message (i.e., a line).

        Args:
            statement (string): String of statement part.

        Returns:
            words (list): Segmented words.
            symbols (list): Separator symbol strings. The length is
                always len(words)+1, which includes
                ones before first word and ones after last word.
                Some of the symbols can be empty string.
        """
        parts = [statement]
        flags = [_FLAG_UNKNOWN]

        for act in self._l_act:
            parts, flags = act.do(parts, flags)
        return self._separate(parts, flags)


class _ActionBase(ABC):

    @abstractmethod
    def do(self, input_parts, input_flags):
        raise NotImplementedError

    @staticmethod
    def _get_blocks(part, a_char_flags):
        # get blocks of continuous same flags
        ret_parts = []
        ret_flags = []
        changeidx = np.where(np.diff(a_char_flags) != 0)[0] + 1
        iterobj = zip(np.append(np.array([0]), changeidx),
                      np.append(changeidx, np.array(len(part))))
        for new_part_start, new_part_end in iterobj:
            ret_parts.append(part[new_part_start:new_part_end])
            ret_flags.append(a_char_flags[new_part_start])
        return ret_parts, ret_flags


class Fix(_ActionBase):
    """Add Fixed flag to matched parts.

    Fixed parts will not be segmented by following actions.
    Fixed parts are selected by regular expression of given pattern.

    Args:
        patterns (str or list of str):
            Regular expression patterns.
            If multiple patterns are given, they are matched
            with every word in order.
    """

    def __init__(self, patterns):
        self._init_patterns(patterns)

    def _init_patterns(self, patterns):
        if isinstance(patterns, str):
            self._l_regex = [re.compile(patterns)]
        else:
            self._l_regex = [re.compile(p) for p in patterns]

    def do(self, input_parts, input_flags):
        """Apply this action to every part.
        Matched parts will be fixed.
        This function works as like a filter of the statement.

        Args:
            input_parts (list of str): partially segmented statement.
            input_flags (list of integer): annotation of input_parts.

        Returns:
            list of str: parts after this action. In the case of Fix action
                (not FixPartial), this return value is same as input_parts.
            list of integer: annotation of the returned parts.
        """
        ret_parts = input_parts[:]
        ret_flags = input_flags[:]
        for i, (s, flag) in enumerate(zip(input_parts, input_flags)):
            if flag != _FLAG_UNKNOWN:
                continue
            for reobj in self._l_regex:
                m = reobj.match(s)
                if m:
                    ret_flags[i] = _FLAG_FIXED
        return ret_parts, ret_flags


class _FixPartialBase(Fix, ABC):

    # private attributes for child classes
    _rest_flag = None
    _fix_groups = None

    def _fix_partially(self, part, mo):
        a_stat = np.array([self._rest_flag] * len(part))
        for fix_group in self._fix_groups:
            a_stat[mo.start(fix_group):mo.end(fix_group)] = _FLAG_FIXED
        return self._get_blocks(part, a_stat)

    def do(self, input_parts, input_flags):
        ret_parts = []
        ret_flags = []
        for part, flag in zip(input_parts, input_flags):
            if flag != _FLAG_UNKNOWN:
                continue
            for reobj in self._l_regex:
                mo = reobj.match(part)
                if mo:
                    # separate part into fixed and others
                    tmp_parts, tmp_flags = self._fix_partially(part, mo)
                    ret_parts += tmp_parts
                    ret_flags += tmp_flags
                else:
                    # leave as is
                    ret_parts.append(part)
                    ret_flags.append(flag)
        return ret_parts, ret_flags


class FixPartial(_FixPartialBase):
    """Extended Fix action to accept complicated patterns.

    Usual Fix action consider the matched part as a word, and fixed.
    In contrast, FixPartial allow the matched part
    to include multiple fixed words or separators.

    Usecase 1:
        e.g., source 192.0.2.1.80 initialized.
        If you intend to consider 192.0.2.1.80 as a combination
        of two different word: IPv4 address 192.0.2.1 and port number 80,
        this cannot be segmented with simple Fix and Split actions.
        After Split action with white space,
        FixPartial can fix the two variables with pattern such as
        r'^(?P<ipaddr>(\\d{1,3}\\.){3}\\d{1,3})\\.(?P<port>\\d{1,5})$'.
    Usecase 2:
        e.g., comment added: "This is a comment description".
        If you intend to consider the comment (strings between parenthesis)
        as a word without segmentation,
        this cannot be achieved with with simple Fix and Split actions.
        FixPartial can fix the comment part
        with pattern r'^.*?"(?P<fix>.+?)".*$' and rest_remove=False.
        After following Split action with '":. ',
        this statement is appropriately segmented.
        Note: Consider using FixParenthesis to easily handle this case.

    Args:
        patterns (str or list of str): Regular expression patterns.
            If multiple patterns given, the first matched pattern
            is used to Fix the part.
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


class FixParenthesis(_FixPartialBase):
    """Extended FixPartial easily used to fix strings between parenthesis.

    The basic usage is similar to FixPartial, but
    this class is designed especially for parenthesis,
    and the format of patterns is simpler.
    For example, FixParenthesis with pattern ['"', '"'] work samely as
    FixPartial with pattern r'^.*?"(?P<fix>.+?)".*$'.

    Each pattern is a 2-length list of left and right parenthesis.
    The left and right pattern can consist of multiple characters,
    such as ["<!--", "-->"].

    Note: If a statement has multiple pairs of parenthesis,
    you need to add multiple FixParenthesis action to StatementParser actions.
    This is because FixParenthesis accept only one fix_group.
    """
    key_fix = "fix"
    _rest_flag = _FLAG_UNKNOWN
    _fix_groups = [key_fix, ]

    def _init_patterns(self, patterns):
        if isinstance(patterns, str):
            self._l_regex = [self._init_pattern(patterns)]
        elif len(patterns) == 2 and isinstance(patterns[0], str):
            self._l_regex = [self._init_pattern(patterns)]
        else:
            self._l_regex = [self._init_pattern(pattern)
                             for pattern in patterns]

    @classmethod
    def _init_pattern(cls, parent_pattern):
        # non-greedy match
        assert len(parent_pattern) == 2
        p_left = parent_pattern[0]
        p_right = parent_pattern[1]
        restr = r'^.*?' + re.escape(p_left) + \
                '(?P<' + cls.key_fix + r'>.+?)' + \
                re.escape(p_right) + r'.*$'
        return re.compile(restr)


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
        if ipaddr:
            try:
                ipaddress.ip_address(string)
            except ValueError:
                pass
            else:
                return True
        if ipnet:
            try:
                ipaddress.ip_network(string, strict=False)
            except ValueError:
                pass
            else:
                return True
        return False

    def do(self, input_parts, input_flags):
        """same as Fix.do"""
        ret_flags = input_flags[:]
        for i, (s, flag) in enumerate(zip(input_parts, input_flags)):
            if flag != _FLAG_UNKNOWN:
                continue
            if self._is_ipaddr(s, self._test_addr, self._test_net):
                ret_flags[i] = _FLAG_FIXED
        return input_parts, ret_flags


class Split(_ActionBase):
    """Split parts by given separators.

    For example, separators ' .' translates
        ['This is a statement.'] -> ['This', 'is', 'a', 'statement']
    The separators (white spaces in this case) will not be considered
    in further actions.

    Args:
        separators (str or list of str): separator symbol strings.
            If iterable, they are all used for segmentation.
            Internally escaped, so you do not need escape sequence in.
    """

    def __init__(self, separators):
        if not isinstance(separators, str):
            separators = "".join(separators)
        restr = r'([' + re.escape(separators) + '])+'
        self._regex = re.compile(restr)

    def _split_part(self, part, iterable_mo):
        a_stat = np.array([_FLAG_UNKNOWN] * len(part))
        for mo in iterable_mo:
            a_stat[mo.start():mo.end()] = _FLAG_SEPARATORS
        return self._get_blocks(part, a_stat)

    def do(self, input_parts, input_flags):
        """Apply this action to all parts.
        This function works as like a filter of the statement.

        Args:
            input_parts (list of str): partially segmented statement.
            input_flags (list of integer): annotation of input_parts.

        Returns:
            list of str: parts after this action.
            list of integer: annotation of the returned parts.
        """
        ret_parts = []
        ret_flags = []
        for part, flag in zip(input_parts, input_flags):
            if flag == _FLAG_UNKNOWN:
                matchobjs = self._regex.finditer(part)
                tmp_parts, tmp_flags = self._split_part(part, matchobjs)
                ret_parts += tmp_parts
                ret_flags += tmp_flags
            else:
                ret_parts.append(part)
                ret_flags.append(flag)
        return ret_parts, ret_flags


class _Reformat(_ActionBase):

    def do(self, input_parts, input_flags):
        ret_parts = []
        ret_flags = []
        prev_isword = True
        for i, (part, flag) in enumerate(zip(input_parts, input_flags)):
            current_isword = flag in (_FLAG_FIXED, _FLAG_UNKNOWN)
            if current_isword and prev_isword:
                # separator is missing: add empty separator
                ret_parts += ["", part]
                ret_flags += [_FLAG_SEPARATORS, _FLAG_FIXED]
            elif not current_isword and not prev_isword:
                # continuous separator: merge into 1 separator
                ret_parts[-1] = ret_parts[-1] + part
            else:
                # as is
                ret_parts.append(part)
                ret_flags.append(flag)
            prev_isword = current_isword
        else:
            if prev_isword:
                ret_parts.append("")
                ret_flags.append(_FLAG_SEPARATORS)
        return ret_parts, ret_flags
