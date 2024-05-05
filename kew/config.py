import yaml

from .handlers import get_handler
from .matcher import prepare_patterns, event_does_match_any_pattern

VERSION = 1


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
        self.include = prepare_patterns(include)
        self.exclude = prepare_patterns(exclude)

    def does_match(self, event):
        if self.include is not None:
            if not event_does_match_any_pattern(event, self.include):
                return False
        if self.exclude is not None:
            if event_does_match_any_pattern(event, self.exclude):
                return False
        return True
