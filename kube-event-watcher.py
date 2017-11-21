#!/usr/bin/env python3

import sys
import signal
import logging
import argparse
import datetime

import requests
import kubernetes.client
import kubernetes.client.rest
import kubernetes.config

log = logging.getLogger(__name__)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--in-cluster', action='store_true', help='configure with in cluster kubeconfig')
    arg_parser.add_argument('--log-level', default='WARNING')
    arg_parser.add_argument('--slack-hook-url')
    args = arg_parser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=args.log_level)

    if args.in_cluster:
        kubernetes.config.load_incluster_config()
    else:
        kubernetes.client.configuration.host = 'http://127.0.0.1:8001'

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    watcher = Watcher()

    watcher.handlers.append(print_handler)
    if args.slack_hook_url:
        watcher.handlers.append(SlackHandler(args.slack_hook_url))

    watcher.watch()


class Watcher:
    def __init__(self):
        self.handlers = []

    def watch(self):
        w = kubernetes.watch.Watch()
        v1 = kubernetes.client.CoreV1Api()

        start_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

        for change in w.stream(v1.list_event_for_all_namespaces):
            event = change['object']
            change_type = change['type']

            if change_type not in ('ADDED', 'MODIFIED'):
                log.info('Skipping change type %s: %s', change_type, event)
                continue

            if event.last_timestamp < start_time:
                log.info('Supressed event from the past: %s', event)
                continue

            for handler in self.handlers:
                handler(event)


def print_handler(event):
    print(event)
    print()


class SlackHandler:
    def __init__(self, hook_url):
        self.hook_url = hook_url

    def __call__(self, event):
        attachment = {
            'color': 'warning' if event.type.lower() == 'warning' else 'good',
            'fallback': '{}: {}'.format(event.metadata.namespace, event.message),
            'fields': [{
                'title': 'Namespace',
                'value': event.metadata.namespace,
                'short': True,
            }, {
                'title': 'Message',
                'value': event.message.strip(),
            }, {
                'title': 'Object',
                'value': '{} {}'.format(event.involved_object.kind, event.involved_object.name),
                'short': True,
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
                'value': format_event_source(event.source),
            }],
        }

        payload = {
            'attachments': [attachment],
        }

        requests.post(self.hook_url, json=payload, timeout=5)


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


def format_event_source(source):
    if source.host:
        return '{}, {}'.format(source.component, source.host)
    else:
        return source.component


def shutdown(signum, frame):
    """
    Shutdown is called if the process receives a TERM signal. This way
    we try to prevent an ugly stacktrace being rendered to the user on
    a normal shutdown.
    """
    log.info("Shutting down")
    sys.exit(0)


if __name__ == '__main__':
    main()
