import json
import unittest

from gvsigol_core.project_package.scrub import scrub_json_tree, assert_no_password_leak


class ScrubTests(unittest.TestCase):
    def test_scrub_password_field(self):
        d = scrub_json_tree({'user': 'u', 'password': 'secret'})
        self.assertEqual(d['password'], '****')

    def test_assert_no_password_leak_passes_on_scrubbed(self):
        t = json.dumps(scrub_json_tree({'password': '****'}))
        assert_no_password_leak(t)

    def test_assert_no_password_leak_raises(self):
        with self.assertRaises(ValueError):
            assert_no_password_leak('{"password": "x"}')


if __name__ == '__main__':
    unittest.main()
