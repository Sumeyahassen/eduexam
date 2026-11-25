"""
Smoke tests for the core app.
These run in CI to ensure Django is correctly configured.
"""
from django.test import TestCase


class CoreSmokeTest(TestCase):
    """Basic sanity checks — verifies Django bootstraps correctly."""

    def test_true(self):
        """Trivial test: CI exits 0 only when at least one test is collected."""
        self.assertTrue(True)
