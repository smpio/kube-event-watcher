import re
import queue
import logging
import fnmatch
import argparse

import kubernetes.client

from utils.kubernetes.config import configure
from utils.signal import install_shutdown_signal_handlers
from utils.kubernetes.watch import KubeWatcher, WatchEventType
from utils.threading import SupervisedThread, SupervisedThreadGroup

from .format import format_event
from .handlers.stdout import stdout_handler
from .handlers.slack import SlackHandler

log = logging.getLogger(__name__)
extended_pat_re = re.compile(r'.*\(.*\)')


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--master', help='kubernetes api server url')
    arg_parser.add_argument('--in-cluster', action='store_true', help='configure with in-cluster config')
    arg_parser.add_argument('--log-level', default='WARNING')
    arg_parser.add_argument('--slack-hook-url', help='send events to Slack')
    arg_parser.add_argument('--stdout', action='store_true', help='print events to stdout')
    arg_parser.add_argument('--ignore', help='comma separated Kind:Namespace/Name:Reason glob patterns to ignore',
                            type=lambda x: x.split(','), default=[])
    args = arg_parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=args.log_level)

    configure(args.master, args.in_cluster)
    install_shutdown_signal_handlers()

    handlers = []
    if args.stdout:
        handlers.append(stdout_handler)
    if args.slack_hook_url:
        handlers.append(SlackHandler(args.slack_hook_url))

    q = queue.Queue()
    threads = SupervisedThreadGroup()
    threads.add_thread(WatcherThread(q, args.ignore))
    threads.add_thread(HandlerThread(q, handlers))
    threads.start_all()
    threads.wait_any()


class HandlerThread(SupervisedThread):
    def __init__(self, queue, handlers):
        super().__init__()
        self.queue = queue
        self.handlers = handlers

    def run_supervised(self):
        while True:
            event = self.queue.get()
            for handle in self.handlers:
                try:
                    handle(event)
                except Exception:
                    log.exception('Failed to handle event')


class WatcherThread(SupervisedThread):
    def __init__(self, queue, ignore_patterns=None):
        super().__init__(daemon=True)
        self.queue = queue
        self.ignore_patterns = ignore_patterns or []
        self.resource_version = None
        self.ignore_patterns = [b for b in (clean_pattern(a) for a in self.ignore_patterns) if b]

    def run_supervised(self):
        v1 = kubernetes.client.CoreV1Api()
        watcher = iter(KubeWatcher(v1.list_event_for_all_namespaces))

        for event_type, event in watcher:
            if event_type == WatchEventType.DONE_INITIAL:
                break

        for event_type, event in watcher:
            if event_type != WatchEventType.ADDED:
                continue
            if self.is_ignored(event):
                continue
            self.queue.put(event)

    def is_ignored(self, event):
        event._formatted = formatted = format_event(event)

        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(formatted, pattern):
                log.info('Suppressed event %s matching pattern %s', formatted, pattern)
                return True

        return False


def clean_pattern(pat):
    pat = pat.strip()
    if not pat:
        return pat

    if not extended_pat_re.fullmatch(pat):
        pat += '(*)'
    return pat


if __name__ == '__main__':
    main()
