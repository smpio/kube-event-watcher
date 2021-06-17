#!/usr/bin/env python3

import re
import queue
import logging
import fnmatch
import argparse
import datetime

import requests
import kubernetes.client

from utils.kubernetes.config import configure
from utils.signal import install_shutdown_signal_handlers
from utils.kubernetes.watch import KubeWatcher, WatchEventType
from utils.threading import SupervisedThread, SupervisedThreadGroup

log = logging.getLogger(__name__)

MIN_WATCH_TIMEOUT = 5 * 60
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
        handlers.append(print_handler)
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
        formatted = format_event(event)

        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(formatted, pattern):
                log.info('Suppressed event %s matching pattern %s', formatted, pattern)
                return True

        return False


def print_handler(event):
    print(format_event(event))


class SlackHandler:
    def __init__(self, hook_url):
        self.hook_url = hook_url

    def __call__(self, event):
        if event.involved_object is None:
            log.info('Ignoring event with unknown involved object: %s', event)
            return

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


def format_event_age(event):
    short_age = format_datetime(event.last_timestamp)

    if event.count > 1:
        return '{} (x{} over {})'.format(short_age, event.count, format_datetime(event.first_timestamp))
    else:
        return short_age


def format_datetime(dt):
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    return format_timedelta(now - dt)


def format_timedelta(td):
    seconds = int(td.total_seconds())

    if seconds < -1:
        return '<invalid>'
    if seconds < 0:
        return '0s'
    if seconds < 60:
        return '{}s'.format(seconds)

    minutes = seconds // 60
    if minutes < 60:
        return '{}m'.format(minutes)

    hours = minutes // 60
    if hours < 24:
        return '{}h'.format(hours)

    days = hours // 24
    if days < 365:
        return '{}d'.format(days)

    years = days / 365
    return '{}y'.format(years)


def format_event_source(event):
    source = event.source
    if source.host:
        return f'{source.component}/{source.host}'
    else:
        return source.component


def format_event(event):
    obj = format_involved_object(event)
    kind = format_involved_object_kind(event)
    src = format_event_source(event)
    return f'{kind}:{obj}:{event.reason}({src})'


def format_involved_object(event):
    if event.involved_object.namespace:
        return f'{event.involved_object.namespace}/{event.involved_object.name}'
    else:
        return event.involved_object.name


def format_involved_object_kind(event):
    if event.involved_object.kind:
        return event.involved_object.kind
    else:
        return ''


def clean_pattern(pat):
    pat = pat.strip()
    if not pat:
        return pat

    if not extended_pat_re.fullmatch(pat):
        pat += '(*)'
    return pat


if __name__ == '__main__':
    main()
