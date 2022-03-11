import unittest

import log2seq


class TestParser(unittest.TestCase):

    def test_readme(self):
        mes = ("Jan  1 12:34:56 host-device1 system[12345]: "
               "host 2001:0db8:1234::1 (interface:eth0) disconnected")
        parser = log2seq.init_parser()
        d = parser.process_line(mes)

        import datetime
        ts = d["timestamp"]
        assert ts.month == 1
        assert ts.day == 1
        assert ts.time() == datetime.time(12, 34, 56)
        assert d["words"] == ['system', '12345', 'host', '2001:0db8:1234::1',
                              'interface', 'eth0', 'disconnected']

    def test_apache_errorlog(self):
        input_lines = [
            ("[Wed Oct 11 14:32:52 2000] [error] [client 127.0.0.1] "
             "client denied by server configuration: /export/home/live/ap/htdocs/test"),
            ("[Fri Sep 09 10:42:29.902022 2011] [core:error] "
             "[pid 35708:tid 4328636416] [client 72.15.99.187] "
             "File does not exist: /usr/local/apache2/htdocs/favicon.ico")
        ]
        from log2seq.preset import apache_errorlog_parser
        parser = apache_errorlog_parser()
        for line in input_lines:
            d = parser.process_line(line)
            assert d is not None
