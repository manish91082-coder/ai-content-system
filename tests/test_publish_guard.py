import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from publish_guard import publishing_allowed


class PublishingGuardTests(unittest.TestCase):
    def test_default_is_fail_closed(self):
        self.assertFalse(publishing_allowed("", ""))

    def test_publish_secret_alone_is_not_enough_in_test_mode(self):
        self.assertFalse(publishing_allowed("true", "true"))

    def test_test_mode_off_without_secret_is_blocked(self):
        self.assertFalse(publishing_allowed("false", ""))

    def test_explicit_authorization_allows_publish(self):
        self.assertTrue(publishing_allowed("false", "true"))

    def test_boolean_values_are_supported(self):
        self.assertTrue(publishing_allowed(False, True))
        self.assertFalse(publishing_allowed(True, True))


if __name__ == "__main__":
    unittest.main()
