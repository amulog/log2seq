# coding: utf-8

from collections.abc import Iterable

# keys in public
KEY_TIMESTAMP = "timestamp"
KEY_STATEMENT = "message"
KEY_WORDS = 'words'
KEY_SYMBOLS = 'symbols'


class ParserDefinitionError(Exception):
    pass


class LogParseFailure(Exception):
    pass


class LogParser:

    def __init__(self, header_parsers, statement_parser):
        from .header import _HeaderParserBase
        if isinstance(header_parsers, Iterable):
            self.header_parsers = header_parsers
        elif isinstance(header_parsers, _HeaderParserBase):
            self.header_parsers = [header_parsers]
        else:
            raise TypeError
        self.statement_parser = statement_parser

    def process_header(self, line):
        for p in self.header_parsers:
            ret = p.process_line(line)
            if ret is not None:
                break
        else:
            if len(line) > 50:
                tmp_msg = line[:50]
            else:
                tmp_msg = line
            msg = "header format mismatch: {0}".format(tmp_msg)
            raise LogParseFailure(msg)
        return ret

    def process_line(self, line):
        """Parse a log message (i.e., a line).

        Args:
            line (str): A log message. Line feed code will be removed.

        Returns:
            """
        line = line.rstrip("\n")
        if line == "":
            return None
        d = self.process_header(line)
        mes = d[KEY_STATEMENT]
        if mes:
            l_w, l_s = self.statement_parser.process_line(mes)
            d[KEY_WORDS] = l_w
            d[KEY_SYMBOLS] = l_s
        return d


def init_parser(header_parser=None, statement_parser=None):
    if header_parser is None:
        from . import preset
        header_parser = preset.default_header_parsers()
    if statement_parser is None:
        from . import preset
        statement_parser = preset.default_statement_parser()
        pass
    return LogParser(header_parser, statement_parser)
