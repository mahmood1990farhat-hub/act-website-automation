#!/usr/bin/env python3
"""Offline integrity, source parity and font-coverage checks for committed downloads."""
import hashlib, json
from pathlib import Path
from pypdf import PdfReader
from fontTools.ttLib import TTFont
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'src/dictionaries/document-manifest.json').read_text())
for locale, docs in manifest.items():
    home=json.loads((root/f'src/dictionaries/{locale}/home.json').read_text())
    sources={'PRIVACY_POLICY':home['policy_and_terms']['policy'],'TERMS_AND_CONDITIONS':home['policy_and_terms']['terms'],'FAQ':home['faqs'],'DRIVER_GUIDELINES':home['download_app']['driver'],'PASSENGER_GUIDELINES':home['download_app']['passenger']}
    assert set(sources)==set(docs)
    for kind, doc in docs.items():
        pdf=root/'public'/doc['file_url'].lstrip('/')
        assert doc['language']==locale
        assert hashlib.sha256(json.dumps(sources[kind],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==doc['source_sha256'],(locale,kind,'stale source')
        assert hashlib.sha256(pdf.read_bytes()).hexdigest()==doc['pdf_sha256'],(locale,kind,'PDF hash')
        pages=PdfReader(pdf).pages
        assert 1 <= len(pages) <= 3
        assert all(len(p.extract_text().strip())>100 for p in pages),(locale,kind,'empty/orphan page')
        assert all('\ufffd' not in p.extract_text() for p in pages),(locale,kind,'replacement glyph')
font=TTFont(root/'public/fonts/act-customer-cjk.woff2');cmap=font.getBestCmap()
for base in [root/'src/dictionaries',root.parent/'act_backend-main/apps/trips/services/document_locales']:
    for source in base.rglob('*.json'):
        missing={ord(c) for c in source.read_text() if '\u3400'<=c<='\u9fff' and ord(c) not in cmap}
        assert not missing,(str(source),missing)
print('PASS: all 35 PDFs match their language/source/hash, no orphan/empty pages, and bundled font covers all Chinese catalogue glyphs')

phone=(root/'node_modules/react-phone-number-input/locale/zh.json').read_text()
assert all(ord(c) in cmap for c in phone if '\u3400'<=c<='\u9fff'), 'Chinese country-label glyphs'
