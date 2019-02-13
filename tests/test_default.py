#!/usr/bin/env python
# coding: utf-8

import log2seq

import message
l_messages = message.messages

if __name__ == "__main__":
    p = log2seq.init_parser()

    for mes in l_messages:
        print(mes)
        dt, host, l_w, l_s = p.process_line(mes)
        print("-> {0} {1} {2}".format(dt, host, l_w))

