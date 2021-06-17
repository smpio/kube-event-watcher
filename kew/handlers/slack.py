import requests

from kew.format import format_involved_object, format_involved_object_kind, format_event_age, format_event_source


class SlackHandler:
    def __init__(self, hook_url):
        self.hook_url = hook_url

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

        resp = requests.post(self.hook_url, json=payload, timeout=5)
        resp.raise_for_status()
