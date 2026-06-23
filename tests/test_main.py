import unittest

from click.testing import CliRunner

from log2seq.__main__ import main


LINES = ("Jan  1 12:34:56 host system[1]: ok one\n"
         "GARBAGE no header at all\n"
         "Feb  2 01:02:03 host app[2]: ok two\n")


class TestMain(unittest.TestCase):

    def _run(self, args, stdin):
        runner = CliRunner(mix_stderr=False)
        return runner.invoke(main, args, input=stdin)

    def test_stdout_stderr_split(self):
        # successes go to stdout; failures + summary go to stderr.
        r = self._run(["-t", "words"], LINES)
        assert r.exit_code == 0
        assert r.stdout.splitlines() == ["system 1 ok one", "app 2 ok two"]
        assert "parse failed:" in r.stderr
        assert "2 ok, 1 failed" in r.stderr

    def test_failures_only_suppresses_stdout(self):
        r = self._run(["--failures-only"], LINES)
        assert r.exit_code == 0
        assert r.stdout == ""
        assert "2 ok, 1 failed" in r.stderr

    def test_exit_1_when_nothing_parses(self):
        r = self._run([], "GARBAGE1\nGARBAGE2\n")
        assert r.exit_code == 1
        assert "0 ok, 2 failed" in r.stderr

    def test_exit_2_on_unloadable_parser(self):
        r = self._run(["-p", "/no/such/parser.py"], "x\n")
        assert r.exit_code == 2

    def test_max_failures_caps_stderr_detail(self):
        r = self._run(["--max-failures", "1"],
                      "G1\nG2\nG3\nJan  1 00:00:00 h a[1]: ok\n")
        assert r.exit_code == 0
        assert r.stderr.count("parse failed:") == 1
        assert "suppressed" in r.stderr
        assert "1 ok, 3 failed" in r.stderr
