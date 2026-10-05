from unittest.mock import patch

from django.test import SimpleTestCase, override_settings


class GoogleMapsClientInitializationTests(SimpleTestCase):
    @override_settings(GOOGLE_MAPS_API_KEY="not-a-real-key")
    @patch("utils.common.google_map.googlemaps.Client")
    def test_import_does_not_construct_google_client(self, client):
        # Importing URL/model modules in management commands and CI must not
        # validate/connect to Google Maps. Client creation belongs to route use.
        import importlib
        import utils.common.google_map as google_map

        importlib.reload(google_map)

        client.assert_not_called()
