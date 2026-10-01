"""Focused source/handler regression without Django, DB, emails or real secrets.

Extract the actual handler AST and execute it with explicit dependency stubs.
These tests are not an HTTP/Django integration test or a full logging audit.
"""
import ast
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parents[1] / 'apps/drivers/views/onboarding_views.py'
TREE = ast.parse(SOURCE.read_text())
VIEW = next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == 'DriverOnboardingStep1View')
HANDLER = next(n for n in VIEW.body if isinstance(n, ast.FunctionDef) and n.name == 'handle_post')
SENTINEL = 'SYNTHETIC_SECRET_MUST_NOT_BE_LOGGED'

class ValidationError(Exception):
    def __init__(self, detail):
        super().__init__(detail); self.detail = detail

class IntegrityError(Exception):
    pass

class DatabaseError(Exception):
    pass

class OnboardingLoggingTests(unittest.TestCase):
    def invoke(self, *, valid=True, error=None, locale='en'):
        serializer = SimpleNamespace(
            is_valid=lambda: valid,
            errors={'confirm_password': [SENTINEL]},
            validated_data={'confirm_password': SENTINEL},
        )
        def save():
            if error is not None: raise error
            return SimpleNamespace(id=12)
        serializer.save = save
        self.factory = Mock(return_value=serializer)
        self.mail = Mock()
        self.admin_mail = Mock()
        self.log = Mock()
        def error_response(message, **kwargs):
            return {'message': message, 'status': kwargs.get('status_code', 400)}
        helpers = SimpleNamespace(
            create_validation_error_response=lambda errors, locale, message: {'errors': errors, 'status': 400},
            create_error_response=error_response,
            create_exception_error_response=Mock(side_effect=AssertionError('Unsafe exception helper called')),
        )
        namespace = {
            'activate': lambda locale: None, 'get_locale': lambda **kwargs: locale,
            'DriverOnboardingQuestionnaireSerializer': self.factory,
            'get_bilingual_error_message': lambda en, ar, loc: ar if loc == 'ar' else en,
            'ValidationError': ValidationError, 'IntegrityError': IntegrityError,
            'DatabaseError': DatabaseError, 'logger': self.log,
            'Response': lambda body, status: {'body': body, 'status': status},
            'status': SimpleNamespace(HTTP_201_CREATED=201, HTTP_400_BAD_REQUEST=400, HTTP_500_INTERNAL_SERVER_ERROR=500),
            '_': lambda text: text,
        }
        module = ast.Module(body=[HANDLER], type_ignores=[])
        exec(compile(module, str(SOURCE), 'exec'), namespace)
        request = SimpleNamespace(data={'password': SENTINEL, 'confirm_password': SENTINEL})
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.dict('sys.modules', {
            'utils.common.error_handlers': helpers,
            'utils.common.email': SimpleNamespace(send_driver_onboarding_submitted=self.mail, send_admin_onboarding_notification=self.admin_mail),
        }), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = namespace['handle_post'](None, request)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')
        self.assertNotIn(SENTINEL, str(self.log.mock_calls))
        helpers.create_exception_error_response.assert_not_called()
        return result

    def test_success_retains_creation_and_email_calls_without_output(self):
        result = self.invoke()
        self.assertEqual(result['status'], 201)
        self.assertEqual(result['body']['onboarding_request_id'], 12)
        self.mail.assert_called_once(); self.admin_mail.assert_called_once()
        self.log.error.assert_not_called()

    def test_invalid_serializer_does_not_print_errors(self):
        self.assertEqual(self.invoke(valid=False)['status'], 400)
        self.mail.assert_not_called()

    def test_save_validation_dict_not_logged(self):
        self.assertEqual(self.invoke(error=ValidationError({'field': [SENTINEL]}))['status'], 400)

    def test_save_validation_list_not_logged(self):
        self.assertEqual(self.invoke(error=ValidationError([SENTINEL]))['status'], 400)

    def test_save_validation_string_not_logged(self):
        self.assertEqual(self.invoke(error=ValidationError(SENTINEL))['status'], 400)

    def test_unexpected_save_error_uses_fixed_response_and_log(self):
        result = self.invoke(error=RuntimeError(SENTINEL))
        self.assertEqual(result['status'], 500)
        self.assertNotIn(SENTINEL, str(result))
        self.log.error.assert_called_once_with('Driver onboarding step 1 save failed.')
        self.mail.assert_not_called()

    def test_arabic_error_response_retained_without_exception_text(self):
        result = self.invoke(error=ValueError(SENTINEL), locale='ar')
        self.assertEqual(result['message'], 'خطأ في إنشاء طلب التسجيل')
        self.assertEqual(result['status'], 500)

    def test_duplicate_email_handling_retained(self):
        result = self.invoke(error=IntegrityError('unique email '+SENTINEL))
        self.assertEqual(result['status'], 400)
        self.assertIn('email', result['message'])
        self.assertNotIn(SENTINEL, str(result))

    def test_duplicate_phone_handling_retained(self):
        result = self.invoke(error=IntegrityError('unique phone '+SENTINEL))
        self.assertEqual(result['status'], 400)
        self.assertIn('phone', result['message'])

    def test_wrapped_database_integrity_handling_retained(self):
        error = DatabaseError(SENTINEL); error.__cause__ = IntegrityError('unique email '+SENTINEL)
        self.assertEqual(self.invoke(error=error)['status'], 400)

    def test_no_debug_or_traceback_calls_in_handler(self):
        for node in ast.walk(HANDLER):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                self.assertNotIn(name, {'print', 'traceback.print_exc', 'traceback.format_exc', 'create_exception_error_response'})
                if name.startswith('logger.'):
                    self.assertTrue(all(isinstance(arg, ast.Constant) for arg in node.args))
                    self.assertEqual(node.keywords, [])

if __name__ == '__main__':
    unittest.main()
