# -*- coding: utf-8 -*-
"""
Discover Django/unittest test cases for the sysadmin test console.

Builds an inventory without executing tests. Classifies database usage from
the test class MRO and assigns a theme from @tag (see django.test.tag) with
heuristic fallbacks.
"""

import inspect
import logging
import re
import unittest
from collections import Counter, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from django.apps import AppConfig, apps
from django.conf import settings
from django.test import TransactionTestCase
from django.test.runner import DiscoverRunner

logger = logging.getLogger(__name__)

# Django test labels: dotted path; ASCII [0-9A-Za-z_.] only (no shell metacharacters).
SYSADMIN_TEST_LABEL_RE = re.compile(r'^[\w.]+\Z', re.ASCII)

# Ordered catalog: first match wins when several theme tags are present.
THEMES: Tuple[str, ...] = ('env', 'geo', 'auth', 'integration', 'other')
THEME_SET = frozenset(THEMES)

# Tags that may appear on tests but must not select a theme bucket.
_IGNORE_TAGS_FOR_THEME = frozenset(
    {
        'slow',
        'fast',
        'no_db',
        'noparallel',
        'parallel',
        'serial',
        'skip',
    }
)

# Apps that are never scanned (library test suites, not deploy tests).
_DEFAULT_SKIP_APP_ROOTS = frozenset(
    {
        'actstream',
        'corsheaders',
        'mozilla_django_oidc',
        'rest_framework',
        'drf_yasg',
        'django_extensions',
        'django_celery_beat',
        'django_celery_results',
    }
)


def _theme_tags_from(tag_set: Set[str]) -> Set[str]:
    return (tag_set - _IGNORE_TAGS_FOR_THEME) & THEME_SET


def _theme_from_tags(tag_set: Set[str]) -> Optional[str]:
    """Pick the first catalog theme present in *tag_set* (THEMES order)."""
    candidates = _theme_tags_from(tag_set)
    if not candidates:
        return None
    for theme in THEMES:
        if theme in candidates:
            return theme
    return None


def _module_stem(module_short: str) -> str:
    if module_short.startswith('test_'):
        return module_short[5:]
    return module_short


def _fallback_theme(module_name: str, app_label: str) -> str:
    """
    When no @tag theme is found, infer a bucket from the test module and app.

    Examples: test_geoenv -> env (substring 'env'); test_geosgeom -> geo.
    """
    short = module_name.rsplit('.', 1)[-1]
    stem = _module_stem(short).lower()
    app_l = (app_label or '').lower()

    if 'integration' in stem:
        return 'integration'
    if stem in ('users', 'user') or stem.startswith('user_') or stem.endswith('_users'):
        return 'auth'
    if 'auth' in stem:
        return 'auth'
    if 'env' in stem:
        return 'env'
    if stem.startswith('geo') or 'geos' in stem or 'ogr' in stem or 'gis' in stem:
        return 'geo'
    if 'auth' in app_l:
        return 'auth'
    if 'services' in app_l:
        return 'integration'
    return 'other'


def _resolved_tags(test_cls: type, method_name: str) -> Set[str]:
    tags: Set[str] = set()
    cls_tags = getattr(test_cls, 'tags', None)
    if cls_tags:
        tags |= set(cls_tags)
    method = getattr(test_cls, method_name, None)
    meth_tags = getattr(method, 'tags', None)
    if meth_tags:
        tags |= set(meth_tags)
    return tags


def testcase_needs_db(test_cls: type) -> bool:
    """
    True if the suite will use Django DB fixtures (TransactionTestCase subtree).

    SimpleTestCase / unittest.TestCase (without TransactionTestCase) -> False.
    """
    if not isinstance(test_cls, type):
        return False
    if not issubclass(test_cls, unittest.TestCase):
        return False
    return issubclass(test_cls, TransactionTestCase)


def _walker(suite: unittest.TestSuite) -> Iterable[unittest.TestCase]:
    """Iterate concrete test instances (nested suites)."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _walker(item)
        else:
            yield item


def _discover_runner_kwargs() -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        'verbosity': 0,
        'interactive': False,
        'failfast': False,
    }
    try:
        parameters = inspect.signature(DiscoverRunner.__init__).parameters
    except (TypeError, ValueError):
        return kwargs
    if 'parallel' in parameters:
        kwargs['parallel'] = 1
    return kwargs


def _suite_for_app_label(app_label: str) -> unittest.TestSuite:
    runner = DiscoverRunner(**_discover_runner_kwargs())
    try:
        return runner.build_suite(test_labels=[app_label])
    except Exception:
        logger.exception('Sysadmin test discovery failed for app %r', app_label)
        return unittest.TestSuite()


def _apps_to_scan() -> Iterable[AppConfig]:
    skip_roots = set(_DEFAULT_SKIP_APP_ROOTS)
    extra_skip = getattr(
        settings,
        'GVSIGOL_SYSADMIN_TEST_DISCOVERY_SKIP_APP_NAMES',
        None,
    )
    if extra_skip:
        skip_roots |= set(extra_skip)

    only = getattr(settings, 'GVSIGOL_SYSADMIN_TEST_DISCOVERY_ONLY_APP_NAMES', None)

    for app_config in apps.get_app_configs():
        name = app_config.name
        if name.startswith('django.'):
            continue
        root = name.split('.', 1)[0]
        if root in skip_roots:
            continue
        if only is not None:
            allowed = set(only)
            if root not in allowed and name not in allowed:
                continue
        yield app_config


def resolve_theme(tags: Set[str], module_name: str, app_label: str) -> str:
    """Resolve theme using @tag first, then module/app heuristics."""
    from_tags = _theme_from_tags(tags)
    if from_tags is not None:
        return from_tags
    return _fallback_theme(module_name, app_label)


def _collapse_module_theme(counter: Counter) -> str:
    if not counter:
        return 'other'
    (top, freq) = counter.most_common(1)[0]
    if len(counter) > 1 and freq == counter.most_common(2)[1][1]:
        for theme in THEMES:
            if counter.get(theme) == freq:
                return theme
    return top


def discover_tests_payload() -> Dict[str, Any]:
    """
    Build the JSON-ready inventory for GET .../tests/discover/.

    Returns keys ``modules`` and ``themes`` as described in the sysadmin plugin
    plan.
    """
    grouped: Dict[str, Dict[str, Any]] = {}
    theme_votes: Dict[str, Counter] = defaultdict(Counter)

    for app_config in _apps_to_scan():
        suite = _suite_for_app_label(app_config.label)
        tests_found = False
        for test in _walker(suite):
            if not hasattr(test, '_testMethodName'):
                continue
            test_cls = test.__class__
            method_name = test._testMethodName
            mod_name = test_cls.__module__
            if (
                mod_name == 'unittest.loader'
                or test_cls.__name__ == '_FailedTest'
            ):
                continue

            tests_found = True
            label = '{0}.{1}.{2}'.format(mod_name, test_cls.__name__, method_name)
            tag_set = _resolved_tags(test_cls, method_name)
            needs_db = testcase_needs_db(test_cls)
            theme = resolve_theme(tag_set, mod_name, app_config.label)

            entry = grouped.setdefault(
                mod_name,
                {
                    'label': mod_name,
                    'app': app_config.label,
                    'needs_db': False,
                    'tests': [],
                },
            )
            entry['needs_db'] = entry['needs_db'] or needs_db
            theme_votes[mod_name][theme] += 1
            entry['tests'].append(
                {'id': label, 'name': method_name, 'needs_db': needs_db, 'theme': theme}
            )

        if not tests_found:
            continue

    modules_out: List[Dict[str, Any]] = []
    for mod_name in sorted(grouped.keys()):
        entry = grouped[mod_name]
        tests_sorted = sorted(entry['tests'], key=lambda t: t['name'])
        collapsed = _collapse_module_theme(theme_votes[mod_name])
        modules_out.append(
            {
                'label': entry['label'],
                'app': entry['app'],
                'theme': collapsed,
                'needs_db': entry['needs_db'],
                'tests': [
                    {'id': t['id'], 'name': t['name'], 'needs_db': t['needs_db']}
                    for t in tests_sorted
                ],
            }
        )

    return {'modules': modules_out, 'themes': list(THEMES)}


def list_discovered_test_ids() -> List[str]:
    """Flat list of Django test labels (for validation / whitelist)."""
    payload = discover_tests_payload()
    out: List[str] = []
    for mod in payload['modules']:
        for test in mod['tests']:
            out.append(test['id'])
    return out


def validate_sysadmin_test_labels(labels, allowed=None):
    # type: (Any, Optional[Set[str]]) -> Tuple[bool, Optional[str], Optional[List[str]]]
    """
    Each label must be a non-empty str, match SYSADMIN_TEST_LABEL_RE, and appear
    in the discovery whitelist.

    Return (True, None, None) on success.

    On failure return (False, message, unknown_list) where *unknown_list* is a
    non-empty list of labels not in the whitelist, or None for other errors
    (pattern, type, empty).
    """
    if not labels:
        return False, 'At least one test label is required', None
    if allowed is None:
        allowed = frozenset(list_discovered_test_ids())
    cleaned = []
    for raw in labels:
        if not isinstance(raw, str):
            return False, 'Each label must be a string', None
        lbl = raw.strip()
        if not lbl:
            return False, 'Empty label is not allowed', None
        if not SYSADMIN_TEST_LABEL_RE.match(lbl):
            return False, 'Invalid characters in label: %s' % lbl, None
        cleaned.append(lbl)
    unknown = [lbl for lbl in cleaned if lbl not in allowed]
    if unknown:
        return False, 'Unknown test label(s)', unknown
    return True, None, None
