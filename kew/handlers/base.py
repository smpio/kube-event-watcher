import json

from kew.format import format_involved_object, format_involved_object_kind, format_event_age, format_event_source

TEMPLATE_GLOBALS = {
    'escape_json': lambda s: json.dumps(s)[1:-1],
    'format_involved_object': format_involved_object,
    'format_involved_object_kind': format_involved_object_kind,
    'format_event_age': format_event_age,
    'format_event_source': format_event_source,
}


class BaseHandler:
    def __init__(self, config):
        self.template_context_script = config.pop('template_context', None)
        self.template = config.pop('template', '{event.message}')

    def format(self, event):
        context = {
            'event': event,
        }

        if self.template_context_script:
            exec(self.template_context_script, TEMPLATE_GLOBALS, context)

        return eval(f'f{self.template!r}', TEMPLATE_GLOBALS, context)

    def __call__(self, event):
        raise NotImplementedError
