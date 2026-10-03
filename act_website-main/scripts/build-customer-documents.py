#!/usr/bin/env python3
"""Build matching website PDFs from reviewed locale dictionaries; no API calls.
Requires WeasyPrint. Set ACT_CJK_FONT to a Noto Sans CJK SC font for Chinese.
Output is committed with the dictionaries so deployments need no PDF build tool.
"""
import hashlib, html, json, os
from pathlib import Path
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'public/documents'
LOCALES = ('en', 'ar', 'fr', 'de', 'es', 'tr', 'zh-CN')
NAMES = {'en':'English','ar':'العربية','fr':'Français','de':'Deutsch','es':'Español','tr':'Türkçe','zh-CN':'简体中文'}
FONT = os.environ.get('ACT_CJK_FONT')
if not FONT or not Path(FONT).is_file():
    raise SystemExit('Set ACT_CJK_FONT to the Noto Sans CJK SC font path before generating Chinese documents.')
esc = html.escape
manifest = {}
for locale in LOCALES:
    path = ROOT / f'src/dictionaries/{locale}/home.json'
    source = json.loads(path.read_text())
    docs = {
        'PRIVACY_POLICY': ('privacy-policy', source['policy_and_terms']['policy']),
        'TERMS_AND_CONDITIONS': ('terms-and-conditions', source['policy_and_terms']['terms']),
        'FAQ': ('faq', source['faqs']),
        'DRIVER_GUIDELINES': ('driver-instructions', source['download_app']['driver']),
        'PASSENGER_GUIDELINES': ('passenger-instructions', source['download_app']['passenger']),
    }
    manifest[locale] = {}
    for kind, (slug, d) in docs.items():
        title = d['title']
        content = f'<h1>{esc(title)}</h1>'
        if kind.endswith('GUIDELINES'):
            content += f'<p>{esc(d["description"])}</p><h2>{esc(d["instructions"]["title"])}</h2><ol>'
            content += ''.join(f'<li>{esc(d["instructions"][f"step{i}"])}</li>' for i in range(1,5))
            content += f'</ol><p>{esc(d["note"])}</p>'
        else:
            if d.get('desc'): content += f'<p>{esc(d["desc"])}</p>'
            for i, e in enumerate(d['elements'], 1):
                content += f'<section><h2>{i}. {esc(e.get("title",e.get("question","")))}</h2>'
                if e.get('desc') or e.get('answer'): content += f'<p>{esc(e.get("desc",e.get("answer","")))}</p>'
                if e.get('subDesc'): content += '<ul>'+''.join(f'<li>{esc(v)}</li>' for v in e['subDesc'])+'</ul>'
                if e.get('descEnd'): content += f'<p>{esc(e["descEnd"])}</p>'
                content += '</section>'
            content += f'<p class="note">{esc(d["warning"])}</p>'
        fontface = f'@font-face {{font-family: ACTCJK;src: url("{Path(FONT).resolve().as_uri()}");}}' if locale=='zh-CN' else ''
        css = fontface+'''@page {size:A4;margin:18mm 18mm 20mm;@bottom-center {content:counter(page);font:9pt sans-serif;color:#666;}}
        body{font-family:"DejaVu Sans",ACTCJK,sans-serif;font-size:10pt;line-height:1.35;color:#202020;}
        header{border-bottom:3px solid #dfb900;padding-bottom:10px;margin-bottom:12px;font-size:10pt;}
        h1{font-size:20pt;line-height:1.25;margin:0 0 12px;}h2{font-size:11pt;margin:10px 0 4px;break-after:avoid;}
        p{margin:5px 0;orphans:3;widows:3;}li{margin:3px 0;}ul,ol{padding-inline-start:22px;}
        .note{border-top:1px solid #bbb;padding-top:12px;margin-top:12px;font-size:9pt;}
        a{color:inherit;}footer{margin-top:12px;font-size:9pt;}'''
        if kind in ('FAQ', 'PRIVACY_POLICY'): css += '@page{margin:16mm;}body{font-size:9.5pt;line-height:1.3;}h1{font-size:18pt;}h2{font-size:10pt;margin:8px 0 3px;}.note{margin-top:8px;padding-top:8px;}footer{margin-top:8px;}'
        if locale=='zh-CN': css += 'body{font-family:ACTCJK,sans-serif;}'
        direction='rtl' if locale=='ar' else 'ltr'
        markup=f'<!doctype html><html lang="{locale}" dir="{direction}"><head><meta charset="utf-8"><title>{esc(title)}</title><style>{css}</style></head><body><header><bdi>Airport &amp; City Transfer</bdi> · {NAMES[locale]}</header>{content}<footer><bdi>airportandcitytransfer.com · info@airportandcitytransfer.com</bdi></footer></body></html>'
        target=OUTPUT/locale/f'{slug}.pdf';target.parent.mkdir(parents=True,exist_ok=True)
        HTML(string=markup).write_pdf(target)
        # Hash the exact source object so policy edits cannot silently leave a stale download.
        source_hash=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        manifest[locale][kind]={'file_url':f'/documents/{locale}/{slug}.pdf','language':locale,'title':title,'source_sha256':source_hash,'pdf_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
( ROOT/'src/dictionaries/document-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Generated 35 localized PDFs and content-hash manifest.')
