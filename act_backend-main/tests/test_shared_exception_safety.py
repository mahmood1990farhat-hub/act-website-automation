"""Actual helper functions with DRF response stubs; no Django/HTTP claim."""
import ast
import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'utils/common/error_handlers.py'
TREE = ast.parse(SOURCE.read_text())
SENTINEL = 'SYNTHETIC_PASSWORD_AND_PAYMENT_SECRET'
EN = 'An unexpected error occurred. Please try again.'
AR = 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.'


class DangerousStringError(Exception):
    def __str__(self):
        raise AssertionError('Exception must not be stringified')

    def __repr__(self):
        raise AssertionError('Exception must not be represented')


class SharedExceptionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.ns = {
            '__name__': 'isolated_error_handlers',
            'Response': lambda data, status: SimpleNamespace(data=data, status_code=status),
            'status': SimpleNamespace(HTTP_400_BAD_REQUEST=400),
        }
        self.ns['status'].HTTP_500_INTERNAL_SERVER_ERROR = 500
        functions = [node for node in TREE.body if isinstance(node, ast.FunctionDef)]
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), 'exec'), self.ns)

    def invoke(self, error, locale='en', custom_message=None):
        output = io.StringIO()
        with patch('logging.getLogger') as factory, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                raise error
            except Exception as caught:
                response = self.ns['create_exception_error_response'](caught, locale, custom_message)
        factory.return_value.error.assert_called_once_with('Unexpected application error.')
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn(SENTINEL, str(response.data))
        self.assertEqual(response.status_code, 500)
        return response

    def test_unknown_error_never_exposed(self):
        self.assertEqual(self.invoke(Exception(SENTINEL)).data['data']['detail'], EN)

    def test_arabic_generic_response(self):
        self.assertEqual(self.invoke(Exception(SENTINEL), 'ar').data['data']['detail'], AR)

    def test_unknown_locale_falls_back_to_english(self):
        self.assertEqual(self.invoke(Exception(SENTINEL), 'xx').data['message'], EN)

    def test_value_type_and_attribute_errors(self):
        for cls in (ValueError, TypeError, AttributeError):
            with self.subTest(cls=cls):
                self.assertEqual(self.invoke(cls(SENTINEL)).data['data']['detail'], EN)

    def test_provider_database_network_messages(self):
        for prefix in ('stripe', 'database integrity', 'connection timeout', 'network', 'doesnotexist'):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.invoke(Exception(prefix + SENTINEL)).data['data']['detail'], EN)

    def test_error_detail_lookalike_not_parsed(self):
        self.assertEqual(self.invoke(Exception("ErrorDetail(string='" + SENTINEL + "', code='invalid')")).data['data']['detail'], EN)

    def test_exception_not_stringified(self):
        self.assertEqual(self.invoke(DangerousStringError()).data['data']['detail'], EN)

    def test_chained_exception_not_logged(self):
        error = RuntimeError('outer')
        error.__cause__ = Exception(SENTINEL)
        self.invoke(error)

    def test_safe_custom_message_and_envelope_preserved(self):
        response = self.invoke(Exception(SENTINEL), custom_message='Unable to save driver.')
        self.assertEqual(response.data, {'success': False, 'message': 'Unable to save driver.',
                                       'data': {'detail': EN}, 'pagination': None})

    def test_expected_validation_formatter_preserved(self):
        self.assertEqual(self.ns['format_validation_errors']({'email': [['Invalid email', 'بريد غير صحيح']]}, 'en'),
                         {'email': ['Invalid email']})
        self.assertEqual(self.ns['format_validation_errors']({'email': [['Invalid email', 'بريد غير صحيح']]}, 'ar'),
                         {'email': ['بريد غير صحيح']})

    def test_exception_parameter_unused(self):
        node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == 'format_exception_error')
        self.assertFalse(any(isinstance(n, ast.Name) and n.id == 'exception' for n in ast.walk(node)))


if __name__ == '__main__':
    unittest.main()
