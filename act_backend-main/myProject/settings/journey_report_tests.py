"""Use the established isolated PostGIS environment for journey report tests."""

from .tracking_tests import *  # noqa: F401,F403

ROOT_URLCONF = "apps.trips.tests.journey_report_test_urls"
