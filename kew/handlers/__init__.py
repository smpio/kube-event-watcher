from .stdout import stdout_handler
from .slack import SlackHandler

handler_ctors = {
    'stdout': stdout_handler,
    'slack': SlackHandler,
}


def get_handler(config):
    ctor = handler_ctors[config['type']]
    return ctor(config)
