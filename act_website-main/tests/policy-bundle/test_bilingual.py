"""English/Arabic review-file routing only; no website, DB, payments or messages."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import policy_review_bundle as b

SPEC = REPO / 'docs/policy-releases/act-policy-review-bilingual-20261026.json'
IDS = ('customer-booking-terms', 'driver-application-terms', 'driver-privacy-notice')
ENGLISH_HASHES = (
    'abd1079a5304f69cc664f3f3841abdfe17f3545273367b20137ea8e291083327',
    '09afce2c8af0f8925bcf7252a57506f14ca7d9305a3f5c9d6d01d54d48c5e2cd',
    '4da269cb7545e6a2ae438e8530ec44f6c50113e5d054579292f33d67c2c6aee2',
)


class BilingualPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.tmp.name)
        cls.output = cls.work / 'review'
        cls.spec = b.load_spec(SPEC)
        cls.source_before = {d['source']: (REPO / d['source']).read_bytes() for d in cls.spec['documents']}
        with patch('socket.socket.connect', side_effect=AssertionError('External access forbidden')):
            cls.receipt = b.build_bundle(SPEC, cls.output, REPO)
        cls.links = json.loads((cls.output / 'document-links.candidate.json').read_text())
        cls.release = json.loads((cls.output / 'checkout-release.candidate.json').read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def changed_spec(self, fn):
        spec = copy.deepcopy(self.spec); fn(spec)
        path = self.work / 'changed.json'; path.write_text(b.dump(spec))
        return path

    def copy_bundle(self):
        path = self.work / 'changed'
        if path.exists(): shutil.rmtree(path)
        shutil.copytree(self.output, path)
        return path

    def test_01_six_documents_and_unchanged_english_text(self):
        self.assertEqual(len(self.receipt['documents']), 6)
        for ident, digest in zip(IDS, ENGLISH_HASHES):
            self.assertEqual(self.receipt['documents'][ident]['text_sha256'], digest)
            self.assertEqual(self.receipt['documents'][ident + '@ar']['translation_of_text_sha256'], digest)

    def test_02_exact_page_language_selects_matching_three_pdf_links(self):
        for locale in ('en', 'ar'):
            selected = b.select_document_links(self.links, locale)
            self.assertEqual(selected['locale'], locale)
            for key in ('checkout_customer_terms', 'driver_application_terms', 'driver_application_privacy'):
                self.assertTrue(selected[key].startswith('/documents/' + locale + '/'))
                self.assertTrue((self.output / selected[key].lstrip('/')).is_file())
        self.assertEqual(self.links['missing_checkout_locales'], [])
        self.assertNotIn('checkout_customer_terms', self.links)  # No global English fallback.

    def test_03_unknown_or_missing_language_never_falls_back(self):
        for locale in ('', 'AR', 'fr', 'zh', 'zh-CN'):
            with self.assertRaises(ValueError): b.select_document_links(self.links, locale)
        links = copy.deepcopy(self.links); del links['locales']['ar']
        with self.assertRaises(ValueError): b.select_document_links(links, 'ar')

    def test_04_checkout_body_and_pdf_hash_match_each_language(self):
        self.assertEqual(set(self.release['locales']), {'en', 'ar'})
        for locale in ('en', 'ar'):
            doc = self.receipt['documents'][b.document_key(IDS[0], locale)]
            entry = self.release['locales'][locale]
            self.assertEqual(entry['text'], (self.output / doc['text_path']).read_text())
            self.assertEqual(entry['sha256'], b.sha(entry['text'].encode()))
            self.assertEqual(entry['pdf_sha256'], b.sha((self.output / doc['pdf_path']).read_bytes()))
        self.assertNotEqual(self.release['locales']['en']['sha256'], self.release['locales']['ar']['sha256'])

    def test_05_swapped_language_links_rejected_even_if_file_hash_updated(self):
        root = self.copy_bundle(); path = root / 'document-links.candidate.json'
        links = copy.deepcopy(self.links)
        links['locales']['ar']['checkout_customer_terms'] = links['locales']['en']['checkout_customer_terms']
        path.write_text(b.dump(links))
        receipt = json.loads((root / 'bundle-manifest.json').read_text())
        receipt['files'][path.name] = b.sha(path.read_bytes())
        (root / 'bundle-manifest.json').write_text(b.dump(receipt))
        with self.assertRaises(ValueError): b.verify_bundle(root)

    def test_06_translation_must_match_pinned_english_revision(self):
        path = self.changed_spec(lambda s: s['documents'][3].update(translation_of_text_sha256='a' * 64))
        output = self.work / 'wrong-revision'
        with self.assertRaises(ValueError): b.build_bundle(path, output, REPO)
        self.assertFalse(output.exists())

    def test_07_missing_duplicate_or_wrong_version_pair_rejected(self):
        for fn in (lambda s: s['documents'].pop(), lambda s: s['documents'].append(s['documents'][3]),
                   lambda s: s['documents'][3].update(version='another-version')):
            with self.assertRaises(ValueError): b.load_spec(self.changed_spec(fn))

    def test_08_all_source_bytes_and_section_structures_preserved(self):
        for name, before in self.source_before.items():
            self.assertEqual((REPO / name).read_bytes(), before)
            self.assertEqual((self.output / 'sources' / Path(name).name).read_bytes(), before)
        for ident in IDS:
            en = (self.output / f'sections/en/{ident}.md').read_text()
            ar = (self.output / f'sections/ar/{ident}.md').read_text()
            self.assertEqual([kind for kind, _ in b.blocks(en)], [kind for kind, _ in b.blocks(ar)])

    def test_09_rtl_html_keeps_contacts_numbers_and_source_as_text(self):
        for ident in IDS:
            page = (self.output / f'previews/ar/{ident}.html').read_text()
            self.assertIn('lang="ar" dir="rtl"', page)
            self.assertIn('مسودة ترجمة عربية للمراجعة', page)
            self.assertIn('dir="ltr" class="ltr"', page)
        rendered = b.arabic_inline('نص <script>test()</script> +44 20 8153 0303')
        self.assertNotIn('<script>', rendered)
        self.assertIn('+44 20 8153 0303', rendered)

    def test_10_real_pdfs_are_nonempty_and_without_replacement_glyphs(self):
        import fitz
        for doc in self.receipt['documents'].values():
            with fitz.open(self.output / doc['pdf_path']) as pdf:
                self.assertGreater(len(pdf), 0)
                for page in pdf:
                    text = page.get_text()
                    self.assertGreater(len(text.strip()), 20)
                    self.assertNotIn('\ufffd', text)
        # Arabic reading order and semantic accuracy still require visual/content review.

    def test_11_review_only_customer_privacy_still_not_fabricated(self):
        self.assertFalse(self.release['published']); self.assertIsNone(self.release['effective_at'])
        self.assertFalse(self.links['runtime_wired'])
        for locale in ('en', 'ar'):
            self.assertIsNone(self.links['locales'][locale]['customer_privacy'])
        b.verify_bundle(self.output)

    def test_12_arabic_text_tamper_cannot_be_relabelled_as_english(self):
        root = self.copy_bundle(); path = root / 'checkout-release.candidate.json'
        release = copy.deepcopy(self.release); release['locales']['ar'] = release['locales']['en']
        path.write_text(b.dump(release))
        receipt = json.loads((root / 'bundle-manifest.json').read_text())
        receipt['files'][path.name] = b.sha(path.read_bytes())
        (root / 'bundle-manifest.json').write_text(b.dump(receipt))
        with self.assertRaises(ValueError): b.verify_bundle(root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
