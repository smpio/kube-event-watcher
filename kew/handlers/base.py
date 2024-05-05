import json

from kew.format import format_involved_object, format_involved_object_kind, format_event_age, format_event_source
from kew.matcher import prepare_patterns, event_does_match_any_pattern

TEMPLATE_GLOBALS = {
    'escape_json': lambda s: json.dumps(s)[1:-1],
    'format_involved_object': format_involved_object,
    'format_involved_object_kind': format_involved_object_kind,
    'format_event_age': format_event_age,
    'format_event_source': format_event_source,
    'prepare_patterns': prepare_patterns,
    'event_does_match_any_pattern': event_does_match_any_pattern,
}


class BaseHandler:
    def __init__(self, config):
        self.globals = dict(TEMPLATE_GLOBALS)
        self.template_context_script = config.pop('template_context', None)
        self.template = config.pop('template', '{event.message}')
        template_context_init_script = config.pop('template_context_init', None)
        if template_context_init_script:
            ctx_locals = {}
            exec(template_context_init_script, self.globals, ctx_locals)
            self.globals.update(ctx_locals)

    def format(self, event):
        context = {
            'event': event,
        }

        if self.template_context_script:
            exec(self.template_context_script, self.globals, context)

        return eval(f'f{self.template!r}', self.globals, context)

    def __call__(self, event):
        raise NotImplementedError
