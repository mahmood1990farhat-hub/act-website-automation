"""Focused policy-artifact checks. No booking, database, provider or mail calls."""
import copy
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import unicodedata
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import policy_review_bundle as bundle

SPEC = REPO / 'docs/policy-releases/act-policy-review-20261026.json'


class PolicyBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.tmp.name)
        cls.output = cls.work / 'review'
        cls.spec = bundle.load_spec(SPEC)
        cls.source_before = {d['source']: (REPO/d['source']).read_bytes() for d in cls.spec['documents']}
        # Actual WeasyPrint generation, once for the focused suite. Resources and
        # sockets cannot reach live services, even if a renderer regression occurs.
        with patch('socket.socket.connect', side_effect=AssertionError('No network in policy tests')):
            cls.receipt = bundle.build_bundle(SPEC, cls.output, REPO)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def variant_spec(self, change):
        spec = copy.deepcopy(self.spec); change(spec)
        path = self.work / 'changed-spec.json'; path.write_text(bundle.dump(spec), encoding='utf-8')
        return path

    def copied_bundle(self):
        p = self.work / 'copy'
        if p.exists(): shutil.rmtree(p)
        shutil.copytree(self.output, p)
        return p

    def test_01_existing_sources_byte_for_byte_unchanged(self):
        for name, raw in self.source_before.items():
            self.assertEqual((REPO/name).read_bytes(), raw)
            self.assertEqual((self.output/'sources'/Path(name).name).read_bytes(), raw)

    def test_02_customer_and_driver_documents_are_separate(self):
        self.assertEqual(set(self.receipt['documents']), {'customer-booking-terms','driver-application-terms','driver-privacy-notice'})
        customer = (self.output/'texts/en/customer-booking-terms.txt').read_text()
        driver = (self.output/'texts/en/driver-application-terms.txt').read_text()
        self.assertIn('50% of the amount paid', customer)
        self.assertIn('exactly 12 hours before pickup', customer)
        self.assertIn('exclusively self-employed', driver)
        self.assertIn('Self Assessment', driver)
        self.assertNotIn('## Part B', customer)
        self.assertNotIn('Owner/reviewer notes', driver)

    def test_03_refund_safeguard_and_distinct_booking_lead_time_preserved(self):
        txt = (self.output/'texts/en/customer-booking-terms.txt').read_text()
        for phrase in ('Consumer-rights safeguard:', 'ACT will refund the excess',
                       'Online bookings require at least three hours', 'full refund (100%)',
                       '12 hours or less before pickup: no refund under the standard schedule.'):
            self.assertIn(phrase, txt)

    def test_04_descriptor_matches_actual_document_text_and_pdf(self):
        self.assertEqual(bundle.verify_bundle(self.output)['state'], 'review_only')
        release = json.loads((self.output/'checkout-release.candidate.json').read_text())
        doc = self.receipt['documents']['customer-booking-terms']
        self.assertEqual(release['locales']['en']['text'], (self.output/doc['text_path']).read_text())
        self.assertEqual(release['locales']['en']['pdf_sha256'], bundle.sha((self.output/doc['pdf_path']).read_bytes()))

    def test_05_pdf_text_contains_all_canonical_words_in_order(self):
        import fitz
        norm = lambda s: re.sub(r'\s+', '', unicodedata.normalize('NFKC', s))
        for ident, d in self.receipt['documents'].items():
            with self.subTest(document=ident), fitz.open(self.output/d['pdf_path']) as pdf:
                text = ''.join(' '.join(b[4] for b in p.get_text('blocks') if b[1] < p.rect.height-50) for p in pdf)
                canonical = (self.output/d['text_path']).read_text()
                self.assertIn(norm(canonical), norm(text))
                self.assertNotIn('\ufffd', text)
                self.assertTrue(all(p.get_text().strip() for p in pdf))

    def test_06_cannot_publish_or_set_effective_date(self):
        for change in (lambda s:s.update(published=True), lambda s:s.update(effective_at='2026-10-26T00:00:00Z'),lambda s:s.update(state='approved')):
            with self.assertRaises(ValueError): bundle.load_spec(self.variant_spec(change))

    def test_07_missing_arabic_and_customer_privacy_not_invented(self):
        release=json.loads((self.output/'checkout-release.candidate.json').read_text())
        links=json.loads((self.output/'document-links.candidate.json').read_text())
        self.assertEqual(set(release['locales']), {'en'})
        self.assertEqual(links['missing_checkout_locales'], ['ar'])
        self.assertIsNone(links['customer_privacy'])
        self.assertFalse(links['runtime_wired'])

    def test_08_tampered_source_rejected_before_output(self):
        doc=copy.deepcopy(self.spec['documents'][0]); doc['source_sha256']='0'*64
        with self.assertRaises(ValueError): bundle.selected_source(doc, REPO)

    def test_09_missing_or_reversed_section_rejected(self):
        doc=copy.deepcopy(self.spec['documents'][0]); doc['start']='missing marker'
        with self.assertRaises(ValueError): bundle.selected_source(doc, REPO)
        doc=copy.deepcopy(self.spec['documents'][0]); doc['start'],doc['end']=doc['end'],doc['start']
        with self.assertRaises(ValueError): bundle.selected_source(doc, REPO)

    def test_10_source_paths_cannot_escape_or_use_symlink(self):
        for name in ('../outside', '/etc/passwd', 'x/../../source', 'x\\y'):
            with self.assertRaises(ValueError): bundle.relative_file(REPO,name)
        p=self.work/'link';p.symlink_to(SPEC)
        with self.assertRaises(ValueError): bundle.relative_file(self.work,'link')

    def test_11_cannot_overwrite_existing_output(self):
        before=(self.output/'bundle-manifest.json').read_bytes()
        with self.assertRaises(ValueError): bundle.build_bundle(SPEC,self.output,REPO)
        self.assertEqual((self.output/'bundle-manifest.json').read_bytes(),before)

    def test_12_review_output_not_allowed_in_website_public(self):
        fake=self.work/'repo';public=fake/'act_website-main/public';public.mkdir(parents=True)
        with self.assertRaises(ValueError): bundle.assert_output_safe(public/'new',fake)

    def test_13_changed_pdf_or_extra_file_fails_verification(self):
        p=self.copied_bundle();doc=self.receipt['documents']['customer-booking-terms']
        with (p/doc['pdf_path']).open('ab') as f:f.write(b'changed')
        with self.assertRaises(ValueError): bundle.verify_bundle(p)
        p=self.copied_bundle();(p/'unexpected.txt').write_text('not in manifest')
        with self.assertRaises(ValueError): bundle.verify_bundle(p)

    def test_14_checkout_mismatch_detected_even_with_updated_file_hash(self):
        p=self.copied_bundle();path=p/'checkout-release.candidate.json'
        release=json.loads(path.read_text());release['locales']['en']['text']='different';path.write_text(bundle.dump(release))
        receipt=json.loads((p/'bundle-manifest.json').read_text());receipt['files'][path.name]=bundle.sha(path.read_bytes())
        (p/'bundle-manifest.json').write_text(bundle.dump(receipt))
        with self.assertRaises(ValueError): bundle.verify_bundle(p)

    def test_15_script_and_resource_shaped_text_is_escaped(self):
        doc=self.spec['documents'][0]
        rendered=bundle.markup(doc,'### Example\n\n<script>bad()</script> <img src="https://example.invalid/a">\n')
        self.assertNotIn('<script>',rendered);self.assertNotIn('<img ',rendered)
        self.assertIn('&lt;script&gt;',rendered)

    def test_16_all_publication_holds_retained_and_no_runtime_activation(self):
        for hold in self.spec['publication_holds']:
            self.assertIn(html.escape(hold),(self.output/'index.html').read_text())
        self.assertFalse(self.receipt['published']);self.assertFalse(self.receipt['runtime_wired'])
        self.assertIsNone(self.receipt['effective_at'])
        for d in self.receipt['documents'].values():
            self.assertIn(bundle.WARNING,(self.output/d['preview_path']).read_text())


if __name__=='__main__':
    unittest.main(verbosity=2)
