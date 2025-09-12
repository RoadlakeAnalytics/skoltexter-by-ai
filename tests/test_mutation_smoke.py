"""Smoke test to ensure mutmut's forced-fail check can trigger.

This test intentionally fails when the environment variable
``MUTANT_UNDER_TEST`` is set to ``'fail'``. The mutmut runner sets this
variable during its forced-fail probe to verify that tests can fail under
mutation; if no test fails, mutmut reports "Unable to force test failures"
and the gate fails. This tiny, targeted test avoids modifying production
code while enabling mutmut to perform its check reliably.
"""

import os


def test_forced_fail_smoke():
    """Fail when mutmut requests a forced failure.

    Notes
    -----
    This test intentionally avoids doctest examples because the test
    runner may set ``MUTANT_UNDER_TEST`` to ``'fail'`` during mutmut's
    forced-fail probe. Including doctest examples that assert on that
    environment variable would make the probe non-deterministic.
    """
    if os.environ.get("MUTANT_UNDER_TEST") == "fail":
        # This exception should only be raised during mutmut's forced-fail
        # probe so that mutmut can verify that a failing test exists.
        raise AssertionError("Intentional fail for mutmut forced-fail probe")
    return None
