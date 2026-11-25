"""Synthetic release safeguards. No production actions or real services."""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).parent
BACK = (ROOT/'deploy_route_backend.py').read_text()
FRONT = (ROOT/'deploy_booking_frontend.py').read_text()

class BookingMapReleaseTests(unittest.TestCase):
    def test_scripts_parse(self):
        ast.parse(BACK); ast.parse(FRONT)
    def test_backend_has_no_database_writes(self):
        self.assertNotIn('self.migrate()', BACK)
        self.assertNotIn('self.ensure_backup()', BACK)
        self.assertIn("require(self.applied, 'Existing migration 0009 is absent", BACK)
        self.assertIn("self.atomic_current(RELEASE, BASE)", BACK)
        self.assertIn("self.atomic_current(BASE, RELEASE)", BACK)
        self.assertIn("BOOKING_ROUTE_BACKEND_DEPLOYED_VERIFIED", BACK)
    def test_exact_source_identity(self):
        self.assertIn("APP_SHA = 'c1638d38898eff1363c8bdf07783dbbe9264a220'", BACK)
        self.assertIn("BACKEND_TREE = '365ecd6f1faf2e6cfc4db258390a0741fba7fde7'", BACK)
        self.assertIn("FRONT_TREE = '4c55b72da7637591a276b26ee953bba70dad819d'", FRONT)
        self.assertIn("SOURCE_BASE_SHA = 'ed1fce2a1c3c5aa8aac36f050d231b250658cca4'", FRONT)
        self.assertIn("EXPECTED_CHANGED = {", FRONT)
    def test_deployed_admin_menu_hashes_are_used_for_both_locales(self):
        import ast
        tree = ast.parse(FRONT)
        assign = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'MENU_BEFORE'
                              for target in node.targets))
        pins = ast.literal_eval(assign.value)
        self.assertEqual(pins['en'],
                         'a6d114637a04bd19c6c5e040ec0aa8a39d14e96754a028fb697cb0e7d04898b5')
        self.assertEqual(pins['ar'],
                         '74d793c730338dae888c65fe3dcf5323f8249e661ea5fc3c05fa494898ec64f8')
        self.assertIn('DEPLOYED_ADMIN_LINK_MISSING', FRONT)

    def test_frontend_retention(self):
        self.assertIn("PORT = 'act-booking-map-c1638d3', 3007", FRONT)
        self.assertIn("self.prior.atomic_file(self.site, self.proposed", FRONT)
        self.assertIn("self.prior.atomic_file(self.site, target", FRONT)
        self.assertIn("self.prior.atomic_file(DUMP, self.original_dump", FRONT)
        self.assertIn("STRIPE_TEST_CONFIGURATION_PRESERVED", FRONT)
        self.assertNotIn("3005", FRONT)
    def test_invalid_route_probe_uses_real_newline_delimiter(self):
        import ast
        tree = ast.parse(FRONT)
        read = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute) and node.func.attr == 'rsplit']
        self.assertTrue(any(node.args and isinstance(node.args[0], ast.Constant)
                            and node.args[0].value == b'\n' for node in read))
        # Python should interpret one escaped newline in source, not literal backslash+n.
        self.assertIn("result.rsplit(b'\\n', 1)", FRONT)
        self.assertNotIn("result.rsplit(b'\\\\n', 1)", FRONT)

    def test_requires_new_backend_and_nonbillable_probe(self):
        self.assertIn('EXPECTED_ROUTE_PREVIEW_BACKEND_NOT_ACTIVE', FRONT)
        self.assertIn('EXPECTED_ROUTE_PREVIEW_BACKEND_SOURCE_DIFFERS', FRONT)
        self.assertIn("'http://localhost/api/trips/route-preview/'", FRONT)
        self.assertIn("'invalid_route'", FRONT)
        self.assertIn("'-w', '\\n%{http_code}'", FRONT)

    def test_preflight_and_recovery_guards(self):
        self.assertIn("SITE_HASH = '02a38a93c8176069b252412b8e8c898d05eb349b75f6f0abe24fd7e8eac961be'", FRONT)
        self.assertIn("CURRENT.is_symlink()", BACK)
        self.assertIn("self.resource_snapshot() == self.state['resources']", BACK)
        self.assertIn("self.backend() == self.backend_baseline", FRONT)
        self.assertIn("self.prior.copy_assets", FRONT)
if __name__ == '__main__': unittest.main()
