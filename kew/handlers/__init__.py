from .stdout import StdoutHandler
from .slack import SlackHandler
from .http_post import HttpPostHandler

handler_ctors = {
    'stdout': StdoutHandler,
    'slack': SlackHandler,
    'http_post': HttpPostHandler,
}


def get_handler(config):
    ctor = handler_ctors[config['type']]
    return ctor(config)
