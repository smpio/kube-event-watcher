import requests

from .base import BaseHandler
from kew.errors import HandledError


class HttpPostHandler(BaseHandler):
    def __init__(self, config):
        super().__init__(config)
        self.url = config['url']
        self.method = config.get('method', 'POST')
        self.content_type = config.get('content_type', 'application/json')
        self.timeout = config.get('timeout', 5)

    def __call__(self, event):
        body = self.format(event)
        resp = requests.request(
            method=self.method,
            url=self.url,
            data=body.encode('utf-8'),
            headers={
                'Content-Type': self.content_type,
            },
            timeout=self.timeout
        )
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            raise HandledError(f'{resp.status_code}: {resp.text}')
