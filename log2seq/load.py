#!/usr/bin/env python
# coding: utf-8


def load_from_script(fp):
    """Load external python script that gives log2seq rules.
    You can copy default_script.py, and extend it.
    Then this function can load the extended script by its file path.
    
    Args:
        fp (str): file path of external python script.
        
    Retruns:
        rules (tuple): a tuple of header_rules and split_rules.
    """

    import os.path
    import sys
    from importlib import import_module
    path = os.path.dirname(fp)
    sys.path.append(os.path.abspath(path))
    libname = os.path.splitext(os.path.basename(fp))[0]
    script_mod = import_module(libname)

    return (script_mod.header_rules, script_mod.split_rules)


def load_from_config(fp):
    """Load log2seq rules from configparser text file.
    It basically follow standard configparser grammer,
    but some options for regular expressions ignore
    line feed codes for convenience in configuration writing.
    data/sample.conf provides same rules as default_script.py .

    Args:
        fp (str): file path of configparser text file.
        
    Retruns:
        rules (tuple): a tuple of header_rules and split_rules.
    """

    def _get_list(conf, section, option):
        # ignore line feed
        s = conf[section][option].replace('\r\n', '').replace('\n', '')
        return [r.strip() for r in s.split(',')]

    def _get_re(conf, section, option):
        import re
        # ignore line feed
        s = conf[section][option].replace('\r\n', '').replace('\n', '')
        return re.compile(s)

    import configparser
    conf = configparser.ConfigParser()
    with open(fp) as f:
        conf.read_file(f)

    l_header = _get_list(conf, 'general', 'header_rules')
    header_rules = [_get_re(conf, 'header', name)
                    for name in l_header]

    l_split = _get_list(conf, 'general', 'split_rules')
    split_rules = []
    for rule in l_split:
        if "." in rule:
            action, name = rule.split(".")
            split_rules.append((action, _get_re(conf, action, name)))
        else:
            if rule == "fixip":
                split_rules.append((rule,
                                    (conf.getboolean('general', 'fixip_addr'),
                                     conf.getboolean('general', 'fixip_net'))))
            else:
                raise SyntaxError("action {0} not available".format(rule))

    return (header_rules, split_rules)

