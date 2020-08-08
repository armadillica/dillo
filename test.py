#!/usr/bin/env python
import os
import sys
from typing import Any, Dict

import django
from django.test.runner import DiscoverRunner


class TestRunner(DiscoverRunner):
    """
    This test runner buffers all output to stdout/stderr and only shows the
    output if the test failed.
    """

    def get_test_runner_kwargs(self) -> Dict[str, Any]:
        return {**super().get_test_runner_kwargs(), 'failfast': False, 'verbosity': 2}


if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
    django.setup()
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests"])
    sys.exit(bool(failures))
