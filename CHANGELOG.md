# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `log2seq` console-script entry point, so `log2seq ...` works after install
  (equivalent to `python -m log2seq ...`).
- CLI options `--max-failures N` (cap the failure diagnostics printed to stderr)
  and `--failures-only` (suppress successful results — for parser debugging).

### Changed

- CLI output model: successful results go to stdout (so they can be piped) while
  parse failures and a final `# processed N lines: M ok, K failed` summary go to
  stderr; one failing line no longer aborts the whole run. Exit status is 0 when
  at least one line parses, 1 when nothing parses, and 2 on a startup error
  (e.g. an unloadable parser script). **Breaking:** the CLI flags
  `--as-statement` and `--skip-success` were renamed to `--statement` and
  `--failures-only`.
- Packaging metadata: declare `python_requires>=3.8`, set
  `long_description_content_type="text/x-rst"` so the README renders on PyPI,
  and list Python 3.8–3.12 in the classifiers (matching the CI matrix).

### Fixed

- loghub example parsers (`example/loghub_*/parser.py`) now align their message
  boundary with each dataset's loghub `log_format`, so the parsed message equals
  loghub's `<Content>`, and they parse the full datasets without failures:
  - **Windows**: fixed an import-time crash caused by `ItemGroup([Date()],
    separator="")` building an empty character class; added a rule for header-less
    CBS continuation lines.
  - **Android**: extract the `<Component>` so the message starts at the content.
  - **Apache**: pin `\[<Time>\] \[<Level>\] <Content>` with `full_format` so a
    leading `[client <ip>]` stays in the message.
  - **Thunderbird**: accept `#`-placeholder node names (`#1#`, `#8#/#8#`), make
    the process id optional, and add a rule for tag-less syslog meta-lines.
  - **Mac**: pin `<Component>[<PID>]( (<Address>))?: <Content>` so a leading `[`
    of the content is kept and a `([subpid])` tail is dropped.
  - **Linux**: allow spaces/slashes in `<Component>` (`syslogd 1.4.1`,
    `/sbin/mingetty`) and add a rule for tag-less syslog meta-lines.
  - **Proxifier**: treat `<Program>` as everything up to the first ` - ` (keeps
    names like `git-remote-https.exe`).
- Two-digit year completion is now deterministic. `YearWithoutCentury` and
  `DateConcat(no_century=True)` previously derived the century from
  `datetime.now()`, making the parsed year depend on when the parser ran. They
  now take an explicit `century` argument (default `20`, i.e. 2000-2099, which
  reproduces the previous behavior for runs in this century). Pass
  `century=19` for 1900s logs.
- Declare the `click` dependency in `install_requires` (it was missing, so the
  CLI raised `ImportError` after a fresh `pip install`). Drop the unused
  `numpy` / `python-dateutil` runtime requirements.
- `apache_errorlog_parser` no longer hardcodes the module name `core`, so 2.4
  error lines from other modules (`mpm_event`, `ssl`, `authz_core`, ...) parse
  instead of raising `LogParseFailure`. The module name is now exposed as the
  `modulename` field.
- `TimeZone` no longer raises a raw `IndexError` on a `Z` (UTC) offset. The
  timezone parser is now shared between `Time` and `TimeZone`; previously it was
  duplicated and the `TimeZone` copy had dropped the `Z` case.
- Fractional-second parsing (`Time` and `DemicalSecond`) uses integer-only
  arithmetic, padding/truncating to six digits, so the microsecond value no
  longer depends on floating-point rounding.
- `UnixTime` resolves the epoch value in UTC by default (new `tz` argument)
  instead of the machine's local timezone, so the parsed datetime is
  deterministic. Affects only parsers that use `UnixTime` as the timestamp;
  pass `tz=dateutil.tz.tzlocal()` to keep local time.
- A standalone `TimeZone` item now works in a rule alongside `Time`: it no
  longer collides with `Time`'s internal regex group, and the extracted offset
  is applied to the timestamp (it was written under a key that timestamp
  reconstruction ignored, so it was silently dropped before).
- CLI (`python -m log2seq`): read input lazily instead of `readlines()`, so
  large/compressed files no longer load entirely into memory; validate `--type`
  with `click.Choice`; and close the output file reliably (even on error).
- CLI: detect tar archives by file suffix (`.tar`, `.tar.gz`, `.tgz`, ...)
  instead of a `".tar."` substring, so plain `.tar` / `.tgz` are handled and
  names that merely contain `.tar.` are not misread as archives; open
  `--output` with the same `--encoding` as the input.

## [0.3.1] - 2022-03-29

- Add example scripts for loghub datasets.
- Add header items; support compressed input for `python -m log2seq`.

## [0.3.0] - 2022-03-12

- Parser API refinements.

## [0.2.7] - 2022-03-12

- Earlier release (see git history).

[Unreleased]: https://github.com/amulog/log2seq/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/amulog/log2seq/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/amulog/log2seq/compare/v0.2.7...v0.3.0
[0.2.7]: https://github.com/amulog/log2seq/releases/tag/v0.2.7
