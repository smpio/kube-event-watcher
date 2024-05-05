import re
from fnmatch import fnmatch

extended_pat_re = re.compile(r'.*\(.*\)')


def prepare_patterns(pats):
    if not pats:
        return pats
    return [b for b in (_clean_pattern(a) for a in pats) if b]


def _clean_pattern(pat):
    pat = pat.strip()
    if not pat:
        return pat

    if not extended_pat_re.fullmatch(pat):
        pat += '(*)'
    return pat


def event_does_match_any_pattern(event, patterns):
    return any((fnmatch(event._formatted, pat) for pat in patterns))
