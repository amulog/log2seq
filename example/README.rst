
log2seq Example Scripts
------------

This directory holds example log2seq parser scripts, one per open log dataset.
For how they are designed and verified, see the `Example Parsers
<https://github.com/amulog/log2seq/wiki/Example-Parsers>`_ page in the wiki.


How to try the scripts?
-----------

::

    $ cd loghub_Android
    $ python -m log2seq -i -p parser.py Android_2k.log


Datasets
--------

loghub Datasets
===============

`loghub <https://github.com/logpai/loghub>`_ is a collection of open log datasets.
There are small sample logs (2k lines) in this repository,
and full datasets can be obtained from the link in loghub repository.
The example parser scripts are designed for full datasets, and they also work for smaller examples.
