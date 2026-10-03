"""Isolated SQLite checks of real models/migrations/serializers and public query bodies.
No production database, uploaded files, accounts, email or external APIs are used.
Run: PYTHONPATH=. python apps/admin_panel/tests/test_document_languages.py
"""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from django.conf import settings

BASE = Path(__file__).resolve().parents[3]
settings.configure(SECRET_KEY='offline', INSTALLED_APPS=['django.contrib.auth', 'django.contrib.contenttypes', 'apps.admin_panel'],
                   DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
                   DEFAULT_AUTO_FIELD='django.db.models.BigAutoField', USE_TZ=True)
import django
django.setup()
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.core.management import call_command
from rest_framework.response import Response
from rest_framework import status
from django.utils.translation import activate
from apps.admin_panel.models.instruction_files import InstructionFile

executor = MigrationExecutor(connection)
executor.migrate([('admin_panel', '0001_initial')])
old = executor.loader.project_state([('admin_panel','0001_initial')]).apps.get_model('admin_panel','InstructionFile')
legacy_id = old.objects.create(file_type='FAQ', title='Legacy unknown language', file='unchanged.pdf').pk
executor = MigrationExecutor(connection)
executor.migrate([('admin_panel','0002_instruction_file_language')])
# Import the real serializer file without unrelated admin serializer side effects.
spec = importlib.util.spec_from_file_location('document_serializers', BASE/'apps/admin_panel/serializers/instruction_files.py')
serializers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serializers)
source = ast.parse((BASE/'apps/admin_panel/views/instruction_files.py').read_text())
names = {'InstructionFilePublicListView','InstructionFilePublicDetailView'}
env = dict(EMADBaseView=object, AllowAny=object, InstructionFile=InstructionFile, Response=Response, status=status,
           InstructionFilePublicSerializer=serializers.InstructionFilePublicSerializer, activate=activate,
           get_locale=lambda request: request.query_params.get('locale','en'),
           get_bilingual_error_message=lambda en, ar, locale: ar if locale=='ar' else en,
           create_error_response=lambda message, locale, status_code: Response({'message':message},status=status_code))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.ClassDef) and n.name in names],type_ignores=[]),'public_document_views','exec'),env)

class DocumentLanguageTests(unittest.TestCase):
    def request(self, locale):
        return SimpleNamespace(query_params={'locale':locale,'file_type':'FAQ'},build_absolute_uri=lambda url:url)

    def test_migration_preserves_unverified_legacy(self):
        legacy=InstructionFile.objects.get(pk=legacy_id)
        self.assertEqual(legacy.language,'')
        self.assertEqual(legacy.file.name,'unchanged.pdf')
        self.assertTrue(legacy.is_active)

    def test_exact_language_and_no_fallback(self):
        InstructionFile.objects.exclude(pk=legacy_id).delete()
        for locale,_ in InstructionFile.LANGUAGE_CHOICES:
            InstructionFile.objects.create(file_type='FAQ',language=locale,title=locale,file=f'{locale}.pdf')
        for locale,_ in InstructionFile.LANGUAGE_CHOICES:
            response=env['InstructionFilePublicListView']().handle_get(self.request(locale))
            rows=response.data['data']['instruction_files']
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['language'],locale)
            self.assertTrue(rows[0]['file_url'].endswith(f'{locale}.pdf'))
            self.assertEqual(env['InstructionFilePublicDetailView']().handle_get(self.request(locale),'FAQ').data['data']['language'],locale)
        InstructionFile.objects.filter(language='fr').update(is_active=False)
        self.assertEqual(env['InstructionFilePublicListView']().handle_get(self.request('fr')).data['data']['instruction_files'],[])
        self.assertEqual(env['InstructionFilePublicDetailView']().handle_get(self.request('fr'),'FAQ').status_code,404)
        for invalid in ['', 'zh-TW', '../en', 'EN']:
            self.assertEqual(env['InstructionFilePublicListView']().handle_get(self.request(invalid)).status_code,400)

    def test_unique_pair_and_admin_validation(self):
        InstructionFile.objects.exclude(pk=legacy_id).delete()
        a=InstructionFile.objects.create(file_type='FAQ',language='en',title='A',file='a.pdf')
        b=InstructionFile.objects.create(file_type='FAQ',language='de',title='B',file='b.pdf')
        with self.assertRaises(IntegrityError), transaction.atomic():
            InstructionFile.objects.create(file_type='FAQ',language='en',title='Duplicate',file='c.pdf')
        serializer=serializers.InstructionFileSerializer(b,data={'language':'en'},partial=True)
        self.assertFalse(serializer.is_valid())
        legacy=InstructionFile.objects.get(pk=legacy_id)
        serializer=serializers.InstructionFileSerializer(legacy,data={'title':'Still unknown'},partial=True)
        self.assertFalse(serializer.is_valid())
        serializer=serializers.InstructionFileSerializer(legacy,data={'language':'fr'},partial=True)
        self.assertTrue(serializer.is_valid(),serializer.errors)
        serializer.save()
        legacy.refresh_from_db()
        self.assertEqual(legacy.version,2)
        self.assertEqual(legacy.file.name,'unchanged.pdf')
        # Restore legacy fixture for order-independent tests.
        InstructionFile.objects.filter(pk=legacy_id).update(language='',version=1)
        serializer=serializers.InstructionFileSerializer(data={'file_type':'FAQ','title':'No language'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('language',serializer.errors)

    def test_migration_matches_model(self):
        call_command('makemigrations','admin_panel',dry_run=True,check=True,verbosity=0)

if __name__=='__main__': unittest.main(verbosity=2)
