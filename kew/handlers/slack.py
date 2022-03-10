import requests

from kew.format import format_involved_object, format_involved_object_kind, format_event_age, format_event_source


def slack_handler(config):
    if config.get('compact'):
        return CompactSlackHandler(config)
    else:
        return VerboseSlackHandler(config)


class BaseSlackHandler:
    def __init__(self, config):
        self.hook_url = config['hook_url']
        self.header = config.get('header')


class VerboseSlackHandler(BaseSlackHandler):
    def __call__(self, event):
        obj = format_involved_object(event)
        kind = format_involved_object_kind(event)

        attachment = {
            'color': 'warning' if event.type.lower() == 'warning' else 'good',
            'fallback': f'{kind} {obj}: {event.message}',
            'fields': [{
                'title': 'Namespace',
                'value': event.metadata.namespace,
            }, {
                'title': kind,
                'value': obj,
            }, {
                'title': 'Message',
                'value': event.message.strip(),
            }, {
                'title': 'Reason',
                'value': event.reason,
                'short': True,
            }, {
                'title': 'Type',
                'value': event.type,
                'short': True,
            }, {
                'title': 'Age',
                'value': format_event_age(event),
                'short': True,
            }, {
                'title': 'From',
                'value': format_event_source(event),
            }],
        }

        payload = {
            'attachments': [attachment],
        }

        if self.header:
            payload['text'] = self.header

        resp = requests.post(self.hook_url, json=payload, timeout=5)
        resp.raise_for_status()


class CompactSlackHandler(BaseSlackHandler):
    def __call__(self, event):
        obj = format_involved_object(event)
        kind = format_involved_object_kind(event)
        msg = f'**{kind} {obj} – {event.reason}**\n{event.message.strip()}'
        if self.header:
            msg = f'{self.header}\n{msg}'
        resp = requests.post(self.hook_url, json={
            'text': msg,
        }, timeout=5)
        resp.raise_for_status()
