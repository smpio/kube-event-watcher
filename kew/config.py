import re
from fnmatch import fnmatch

import yaml

from .handlers import get_handler

VERSION = 1
extended_pat_re = re.compile(r'.*\(.*\)')


def load_config(filename):
    config = _load_file(filename)
    if config['version'] != VERSION:
        raise Exception(f'Invalid config version {config["version"]}, expected {VERSION}')
    sinks = {sink_name: get_handler(sink_config) for sink_name, sink_config in config['sinks'].items()}
    mappings = [_clean_mapping(m, sinks) for m in config['mappings']]
    return Config(sinks, mappings)


def _load_file(filename):
    with open(filename, 'r') as f:
        return yaml.load(f, Loader=yaml.CLoader)


def _clean_mapping(m, sinks):
    return Mapping(sinks[m['sink']], m.get('include'), m.get('exclude'))


class Config:
    def __init__(self, sinks, mappings):
        self.sinks = sinks
        self.mappings = mappings


class Mapping:
    def __init__(self, sink, include, exclude):
        self.sink = sink
        self.include = _clean_patterns(include)
        self.exclude = _clean_patterns(exclude)

    def does_match(self, event):
        if self.include is not None:
            if not any((fnmatch(event._formatted, pat) for pat in self.include)):
                return False
        if self.exclude is not None:
            if any((fnmatch(event._formatted, pat) for pat in self.exclude)):
                return False
        return True


def _clean_patterns(pats):
    if not pats:
        return pats
    return [b for b in (_clean_pattern(a) for a in pats) if b]


def _clean_pattern(pat):
    pat = pat.strip()
    if not pat:
        return pat

    if not extended_pat_re.fullmatch(pat):
        pat += '(*)'
    return pat
