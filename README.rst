#######
log2seq
#######

.. image:: https://img.shields.io/pypi/v/log2seq
   :alt: PyPI release
   :target: https://pypi.org/project/log2seq/

.. image:: https://img.shields.io/pypi/pyversions/log2seq
   :alt: Python support
   :target: https://pypi.org/project/log2seq/

.. image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
   :alt: BSD 3-Clause License
   :target: https://opensource.org/licenses/BSD-3-Clause

.. image:: https://travis-ci.com/amulog/log2seq.svg?branch=master
   :alt: Travis CI
   :target: https://travis-ci.com/github/amulog/log2seq

.. image:: https://readthedocs.org/projects/log2seq/badge/?version=latest
   :alt: Documentation Status
   :target: https://log2seq.readthedocs.io/en/latest/?badge=latest


Log2seq is a python package to help parsing syslog-like messages into word sequences
that is more suitable for further automated analysis.
It is based on a procedure customizable with rules in order, using regular expressions.

* Document: https://log2seq.readthedocs.io
* Source: https://github.com/amulog/log2seq
* Bug Reports: https://github.com/amulog/log2seq/issues
* Author: `Satoru Kobayashi <https://github.com/cpflat/>`_
* License: `BSD-3-Clause <https://opensource.org/licenses/BSD-3-Clause>`_


Installation
------------

You can install log2seq with pip.

::

    pip install log2seq


Tutorial
--------

Log2seq is designed mainly for preprocessing of automated log template generation.
Many implementations of template generation methods requires input log messages in segmented format,
but they only support simple preprocessing, using white spaces.
Log2seq enables more flexible preprocessing enough for parsing practical log messages.

For example, sometimes you may face following format of log messages:

::

	Jan  1 12:34:56 host-device1 system[12345]: host 2001:0db8:1234::1 (interface:eth0) disconnected

This message cannot well segmented with :code:`str.split()` or :code:`re.split()`, because the usage of :code:`:` is not consistent.

log2seq processes this message in multiple steps (in default):

#. Process message header (i.e., timestamp and source hostname)
#. Split message body into word sequence by standard symbol strings (e.g., spaces and brackets)
#. Fix words that should not be splitted later (e.g., ipv6 addr)
#. Split words by inconsistent symbol strings (e.g., :code:`:`)

Following is a sample code:

::

	mes = "Jan  1 12:34:56 host-device1 system[12345]: host 2001:0db8:1234::1 (interface:eth0) disconnected"

	import log2seq
	parser = log2seq.init_parser()

	parsed_line = parser.process_line(mes)

Here, you can get the parsed information like:

::

    >>> parsed_line["timestamp"]
    datetime.datetime(2020, 1, 1, 12, 34, 56)

    >>> parsed_line["host"]
    'host-device1'

    >>> parsed_line["words"]
    ['system', '12345', 'host', '2001:0db8:1234::1', 'interface', 'eth0', 'disconnected']

You can see :code:`:` in IPv6 address is left as is, and other :code:`:` are removed.

This example is using a default parser, but you can also customize your own parser.
For defails, please see the document.
