from .stdout import stdout_handler
from .slack import slack_handler

handler_ctors = {
    'stdout': stdout_handler,
    'slack': slack_handler,
}


def get_handler(config):
    ctor = handler_ctors[config['type']]
    return ctor(config)
