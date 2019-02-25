#!/usr/bin/env python
# coding: utf-8

import os.path
import log2seq

import message
l_messages = message.messages

if __name__ == "__main__":
    place = os.path.dirname(__file__) or "."
    place += "/../log2seq/data/sample.conf"
    rules = log2seq.load_from_config(place)
    p = log2seq.LogParser(rules)

    for mes in l_messages:
        print(mes)
        d = p.process_line(mes)
        print("-> {0} {1} {2}".format(d["timestamp"], d["host"], d["words"]))







