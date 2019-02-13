#!/usr/bin/env python
# coding: utf-8

import os.path
import log2seq

import message
l_messages = message.messages

if __name__ == "__main__":
    rules = log2seq.load_from_config(
        os.path.abspath("../log2seq/data/sample.conf"))
    p = log2seq.Parser(rules)

    for mes in l_messages:
        print(mes)
        dt, host, l_w, l_s = p.process_line(mes)
        print("-> {0} {1} {2}".format(dt, host, l_w))







