# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
