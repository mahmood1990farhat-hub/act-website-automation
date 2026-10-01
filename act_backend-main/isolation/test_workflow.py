"""Static workflow safety checks, not evidence of a GitHub runner execution."""
from pathlib import Path
import unittest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/isolated-safety-tests.yml'


class WorkflowSafetyTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()
        self.workflow = yaml.safe_load(self.text)
        self.job = self.workflow['jobs']['isolated-tests']

    def test_isolated_branch_push_and_explicit_manual_only(self):
        self.assertEqual(set(self.workflow['on']), {'push', 'workflow_dispatch'})
        self.assertEqual(self.workflow['on']['push']['branches'], ['codex/isolated-backend-tests-20261001'])
        self.assertEqual(self.workflow['on']['push']['paths'], [
            '.github/workflows/isolated-safety-tests.yml', 'act_backend-main/isolation/**',
            'act_backend-main/tests/test_onboarding_logging.py',
            'act_backend-main/tests/test_shared_exception_safety.py',
            'act_backend-main/utils/common/error_handlers.py',
            'act_backend-main/apps/drivers/views/onboarding_views.py'])
        consent = self.workflow['on']['workflow_dispatch']['inputs']['confirm_synthetic_only']
        self.assertEqual(consent['type'], 'boolean')
        self.assertTrue(consent['required'])
        self.assertFalse(consent['default'])

    def test_hosted_runner_and_bounded_cost(self):
        self.assertEqual(self.job['runs-on'], 'ubuntu-24.04')
        self.assertEqual(self.job['timeout-minutes'], 10)
        self.assertEqual(len(self.workflow['jobs']), 1)
        self.assertEqual(self.workflow['permissions'], {'contents': 'read'})

    def test_branch_and_consent_gate(self):
        gate = self.job['if']
        self.assertIn("github.event_name == 'workflow_dispatch'", gate)
        self.assertIn("github.ref == 'refs/heads/codex/isolated-backend-tests-20261001'", gate)
        self.assertIn('inputs.confirm_synthetic_only == true', gate)
        self.assertIn("github.event_name == 'push'", gate)

    def test_no_production_credentials_or_environment(self):
        self.assertNotIn('environment', self.job)
        self.assertNotIn('secrets.', self.text)
        self.assertNotIn('self-hosted', self.text)
        checkout = self.job['steps'][0]
        self.assertFalse(checkout['with']['persist-credentials'])
        self.assertEqual(checkout['with']['ref'], '${{ github.sha }}')

    def test_container_run_preserves_isolation(self):
        runs = '\n'.join(step.get('run', '') for step in self.job['steps'])
        self.assertIn('run --rm --no-deps tests', runs)
        for forbidden in ('--privileged', '--network', '--env', '--volume', 'workflow run', 'pm2 ', 'systemctl ', 'git push'):
            self.assertNotIn(forbidden, runs)


if __name__ == '__main__':
    unittest.main()
