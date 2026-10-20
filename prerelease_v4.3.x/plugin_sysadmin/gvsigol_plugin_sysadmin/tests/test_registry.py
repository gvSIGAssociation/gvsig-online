# coding: utf-8
# Compatible with Python 3.6+
import unittest

from django.test import SimpleTestCase, TestCase, TransactionTestCase

from gvsigol_plugin_sysadmin.test_registry import (
    SYSADMIN_TEST_LABEL_RE,
    testcase_needs_db,
    validate_sysadmin_test_labels,
)


class _Plain(unittest.TestCase):
    def test_x(self):
        pass


class _Simple(SimpleTestCase):
    def test_x(self):
        pass


class _Txn(TransactionTestCase):
    def test_x(self):
        pass


class _Django(TestCase):
    def test_x(self):
        pass


class TestcaseNeedsDbTests(unittest.TestCase):
    def test_plain_unittest(self):
        self.assertFalse(testcase_needs_db(_Plain))

    def test_simple_test_case(self):
        self.assertFalse(testcase_needs_db(_Simple))

    def test_transaction_test_case(self):
        self.assertTrue(testcase_needs_db(_Txn))

    def test_django_test_case(self):
        self.assertTrue(testcase_needs_db(_Django))


class ValidateSysadminLabelsTests(unittest.TestCase):
    def test_accepts_whitelist(self):
        allowed = frozenset(['pkg.tests.test_m.Mod.test_one'])
        ok, err, unknown = validate_sysadmin_test_labels(
            ['pkg.tests.test_m.Mod.test_one'],
            allowed,
        )
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertIsNone(unknown)

    def test_rejects_shellish_chars_even_if_in_allowed(self):
        allowed = frozenset(['x;rm -rf y'])
        ok, err, unknown = validate_sysadmin_test_labels(
            ['x;rm -rf y'],
            allowed,
        )
        self.assertFalse(ok)
        self.assertIsNone(unknown)
        self.assertIn('Invalid characters', err)

    def test_rejects_not_in_whitelist(self):
        allowed = frozenset(['only.this.label'])
        ok, err, unknown = validate_sysadmin_test_labels(
            ['only.this.label', 'other.label'],
            allowed,
        )
        self.assertFalse(ok)
        self.assertEqual(err, 'Unknown test label(s)')
        self.assertEqual(unknown, ['other.label'])

    def test_label_regex_allows_digits(self):
        self.assertTrue(
            SYSADMIN_TEST_LABEL_RE.match('app.tests.test_1.Case.test_2'),
        )
