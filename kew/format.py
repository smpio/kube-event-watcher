import datetime


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
