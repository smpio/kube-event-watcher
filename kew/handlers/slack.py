from .http_post import HttpPostHandler


class SlackHandler(HttpPostHandler):
    def __init__(self, config):
        if not config.get('template'):
            config['template_context'] = CONTEXT
            if config.get('compact'):
                config['template'] = COMPACT_TEMPLATE
            else:
                config['template'] = VERBOSE_TEMPLATE
        super().__init__(config)


CONTEXT = '''
obj = escape_json(format_involved_object(event))
kind = escape_json(format_involved_object_kind(event))
reason = escape_json(event.reason)
msg = escape_json(event.message)
color = 'warning' if event.type.lower() == 'warning' else 'good'
'''

COMPACT_TEMPLATE = '{{"text": "**{kind} {obj} – {reason}**\\n{msg}"}}'

VERBOSE_TEMPLATE = '''
{{
    "attachments": [{{
        "color": "{color}",
        "fallback": "**{kind} {obj} – {reason}**\\n{msg}",
        "fields": [
            {{
                "title": "Namespace",
                "value": "{escape_json(event.metadata.namespace)}"
            }},
            {{
                "title": "{kind}",
                "value": "{obj}"
            }},
            {{
                "title": "Message",
                "value": "{msg}"
            }},
            {{
                "title": "Reason",
                "value": "{escape_json(event.reason)}",
                "short": true
            }},
            {{
                "title": "Type",
                "value": "{escape_json(event.type)}",
                "short": true
            }},
            {{
                "title": "Age",
                "value": "{escape_json(format_event_age(event))}",
                "short": true
            }},
            {{
                "title": "From",
                "value": "{escape_json(format_event_source(event))}"
            }}
        ]
    }}]
}}
'''
