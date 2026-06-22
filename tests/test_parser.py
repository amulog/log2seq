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
        from log2seq.preset import apache_errorlog_parser
        parser = apache_errorlog_parser()

        # old (2.2) format: severity only, no module / pid
        d = parser.process_line(
            "[Wed Oct 11 14:32:52 2000] [error] [client 127.0.0.1] "
            "client denied by server configuration: /export/home/live/ap/htdocs/test")
        assert d["severityname"] == "error"
        assert d["host"] == "127.0.0.1"
        assert d["message"] == ("client denied by server configuration: "
                                "/export/home/live/ap/htdocs/test")

        # 2.4 format: <module>:<severity>, pid/tid, client
        d = parser.process_line(
            "[Fri Sep 09 10:42:29.902022 2011] [core:error] "
            "[pid 35708:tid 4328636416] [client 72.15.99.187] "
            "File does not exist: /usr/local/apache2/htdocs/favicon.ico")
        assert d["modulename"] == "core"
        assert d["severityname"] == "error"
        assert d["processid"] == 35708
        assert d["threadid"] == 4328636416
        assert d["host"] == "72.15.99.187"
        assert d["message"] == "File does not exist: /usr/local/apache2/htdocs/favicon.ico"

        # modules other than "core" must parse too (regression: was hardcoded).
        d = parser.process_line(
            "[Mon Dec 05 08:10:12.123456 2016] [mpm_event:notice] "
            "[pid 1:tid 2] AH00489: Apache configured")
        assert d["modulename"] == "mpm_event"
        assert d["severityname"] == "notice"
        assert d["message"] == "AH00489: Apache configured"

        d = parser.process_line(
            "[Mon Dec 05 08:10:12.123456 2016] [authz_core:error] "
            "[pid 1:tid 2] [client 1.2.3.4] AH01630: client denied")
        assert d["modulename"] == "authz_core"
        assert d["severityname"] == "error"
        assert d["host"] == "1.2.3.4"
        assert d["message"] == "AH01630: client denied"
