# coding: utf-8

from collections.abc import Iterable

# keys in public
KEY_TIMESTAMP = "timestamp"
KEY_STATEMENT = "message"
KEY_WORDS = 'words'
KEY_SYMBOLS = 'symbols'


class ParserDefinitionError(Exception):
    """ParserDefinitionError is raised when the given rules
    are inappropriate (e.g., having syntax errors).
    """
    pass


class LogParseFailure(Exception):
    """LogParserFailure is raised when the input log message
    not matched with all given HeaderParser rules.

    If you want to pass such mismatching log messages,
    use try-except with this exception.
    """
    pass


class LogParser:
    """Log parser object.

    LogParser in log2seq consists of two different parsers:
    :class:`~header.HeaderParser` and :class:`~statement.StatementParser`.

    Parsed results are returned in one dict object.
    It consists of following parsed information.

    * Header informations (:attr:`~header.Item.value_name` as key)
    * Statement part in string format ("message" as key)
    * Segmented words in statement part ("words" as key)
    * Separator symbols in ststement part ("symbols" as key)

    Example:
        >>> mes = "Jan  1 12:34:56 host-device1 system[12345]: host 2001:0db8:1234::1 (interface:eth0) disconnected"
        >>> parser = log2seq.init_parser()  # get default LogParser
        >>> parsed_line = parser.process_line(mes)
        >>> parsed_line["timestamp"]  # timestamp parsed by HeaderParser
        datetime.datetime(2020, 1, 1, 12, 34, 56)
        >>> parsed_line["host"]  # Hostname item in HeaderParser
        'host-device1'
        >>> parsed_line["message"]  # Statement part parsed by HeaderParser
        'system[12345]: host 2001:0db8:1234::1 (interface:eth0) disconnected'
        >>> parsed_line["words"]  # Segmented words parsed by StatementParser
        ['system', '12345', 'host', '2001:0db8:1234::1', 'interface', 'eth0', 'disconnected']
        >>> parsed_line["symbols"]  # Separator symbols parsed by StatementParser
        ['', '[', ']: ', ' ', ' (', ':', ') ', '']

    You can specify multiple :class:`~header.HeaderParser` as input.
    If so, :class:`LogParser` try to parse a log message with them in order,
    and the first matched rule is used for the message.

    Args:
        header_parsers (:obj:`~header.HeaderParser` or list of it):
            one or multiple HeaderParser instance to use.
        statement_parser (:obj:`~statement.StatementParser`):
            one StatementParser instance to use.
    """

    def __init__(self, header_parsers, statement_parser):
        from .header import _HeaderParserBase
        if isinstance(header_parsers, Iterable):
            self.header_parsers = header_parsers
        elif isinstance(header_parsers, _HeaderParserBase):
            self.header_parsers = [header_parsers]
        else:
            raise TypeError
        self.statement_parser = statement_parser

    def process_header(self, line, verbose=False):
        """Parse header part in a log message.

        This function uses all given HeaderParser rules.
        If all HeaderParser fails to match the input log message,
        it raises a :class:`LogParseFailure` exception.

        Args:
            line (str): A log message.
            verbose (bool, optional): Show intermediate progress
                of applying header rules.

        Returns:
            dict: parsed header data.
        """
        for rule_id, p in enumerate(self.header_parsers):
            ret = p.process_line(line)
            if ret is None:
                if verbose:
                    print("header rule {0}: mismatch".format(rule_id))
            else:
                if verbose:
                    print("header rule {0}: match".format(rule_id))
                break
        else:
            if len(line) > 50:
                tmp_msg = line[:50]
            else:
                tmp_msg = line
            msg = "header format mismatch: {0}".format(tmp_msg)
            raise LogParseFailure(msg)
        return ret

    def process_statement(self, statement, verbose=False):
        """Parse a log statement.

        Args:
            statement (str): Statement part in a log message.
            verbose (bool, optional): Show intermediate progress
                of applying rules.

        Returns:
            tuple: List of two components: words and symbols.
            See :meth:`statement.StatementParser.process_line`.
        """

        return self.statement_parser.process_line(statement, verbose)

    def process_line(self, line, verbose=False):
        """Parse a log message (i.e., a line).

        If all HeaderParser fails to match the input log message,
        it raises a LogParserFailure exception.

        Args:
            line (str): A log message. Line feed code will be removed.
            verbose (bool, optional): Show intermediate progress
                of applying rules.

        Returns:
            dict: parsed data.
        """
        line = line.rstrip("\n")
        if line == "":
            return None
        d = self.process_header(line, verbose)
        mes = d[KEY_STATEMENT]
        l_w, l_s = self.process_statement(mes, verbose)
        d[KEY_WORDS] = l_w
        d[KEY_SYMBOLS] = l_s
        return d


def init_parser(header_parsers=None, statement_parser=None):
    """Generate :class:`LogParser` object.

    If no arguments are given,
    this function generates LogParser with default configurations.

    Args:
        header_parsers (:class:`~header.HeaderParser` or list of it, optional):
            one or multiple HeaderParser instance to use.
            If not given, use :func:`preset.default_header_parsers`.
        statement_parser (:class:`~statement.StatementParser`):
            one StatementParser instance to use.
            If not given, use :func:`preset.default_statement_parser`.
    """

    if header_parsers is None:
        from . import preset
        header_parsers = preset.default_header_parsers()
    if statement_parser is None:
        from . import preset
        statement_parser = preset.default_statement_parser()
    return LogParser(header_parsers, statement_parser)
