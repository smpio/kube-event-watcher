import queue
import logging
import argparse

import kubernetes.client

from utils.kubernetes.config import configure
from utils.signal import install_shutdown_signal_handlers
from utils.kubernetes.watch import KubeWatcher, WatchEventType
from utils.threading import SupervisedThread, SupervisedThreadGroup

from .config import load_config
from .format import format_event

log = logging.getLogger(__name__)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--master', help='kubernetes api server url')
    arg_parser.add_argument('--in-cluster', action='store_true', help='configure with in-cluster config')
    arg_parser.add_argument('--log-level', default='WARNING')
    arg_parser.add_argument('--config', required=True)
    args = arg_parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=args.log_level)
    configure(args.master, args.in_cluster)
    install_shutdown_signal_handlers()
    config = load_config(args.config)

    q = queue.Queue()
    threads = SupervisedThreadGroup()
    threads.add_thread(WatcherThread(q))
    threads.add_thread(HandlerThread(q, config))
    threads.start_all()
    threads.wait_any()


class HandlerThread(SupervisedThread):
    def __init__(self, queue, config):
        super().__init__()
        self.queue = queue
        self.config = config

    def run_supervised(self):
        while True:
            event = self.queue.get()
            self.handle(event)

    def handle(self, event):
        for mapping in self.config.mappings:
            if mapping.does_match(event):
                try:
                    mapping.sink(event)
                except Exception:
                    log.exception('Failed to handle event')


class WatcherThread(SupervisedThread):
    def __init__(self, queue):
        super().__init__(daemon=True)
        self.queue = queue

    def run_supervised(self):
        v1 = kubernetes.client.CoreV1Api()
        watcher = iter(KubeWatcher(v1.list_event_for_all_namespaces))

        for event_type, event in watcher:
            if event_type == WatchEventType.DONE_INITIAL:
                break

        for event_type, event in watcher:
            if event_type != WatchEventType.ADDED:
                continue
            event._formatted = format_event(event)
            self.queue.put(event)


if __name__ == '__main__':
    main()
