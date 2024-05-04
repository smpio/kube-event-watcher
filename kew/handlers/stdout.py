import sys

from .base import BaseHandler


class StdoutHandler(BaseHandler):
    def __init__(self, config):
        config.setdefault('template', '> {event._formatted}\n{event.message}\n')
        super().__init__(config)

    def __call__(self, event):
        sys.stdout.write(self.format(event))
