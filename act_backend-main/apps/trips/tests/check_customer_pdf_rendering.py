"""Render the production PDF function bodies offline, with synthetic bookings only.
Run from backend root. Requires the deployed WeasyPrint dependencies and pypdf.
No database, mail, Google or Stripe calls. Output is disposable test evidence.
"""
import ast, os
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader
from weasyprint import HTML
from apps.trips.tests.test_customer_language import sample, settings, booking_language, render_customer_document
source=Path(settings.BASE_DIR)/'apps/trips/services/pdf_generator.py'
names={'generate_booking_confirmation_pdf','generate_cancellation_confirmation_pdf'}
module=ast.Module(body=[n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
env=dict(globals())
exec(compile(module,str(source),'exec'),env)
out=Path(os.environ.get('ACT_PDF_TEST_OUTPUT','/tmp/act-customer-pdf-check'));out.mkdir(parents=True,exist_ok=True)
for locale in ['ar','fr','de','es','tr','zh-CN']:
    for kind in ['booking','cancellation']:
        result=env[f'generate_{kind}_confirmation_pdf'](sample(locale))
        data=result.getvalue();assert data.startswith(b'%PDF')
        reader=PdfReader(BytesIO(data));assert 1<=len(reader.pages)<=3
        text=''.join(p.extract_text() for p in reader.pages)
        assert 'ACT-000042' in text,(locale,kind)
        assert '\ufffd' not in text,(locale,kind)
        if locale=='zh-CN':
            assert '预订' in text,(kind,'Chinese text')
            fonts=[str(f.get_object().get('/BaseFont')) for p in reader.pages for f in p['/Resources']['/Font'].get_object().values()]
            assert any('ACTCustomerCJK' in f.replace('-', '') for f in fonts),fonts
        (out/f'{kind}-{locale}.pdf').write_bytes(data)
print('PASS: 12 actual booking/cancellation PDF renders across six non-English locales, including embedded Chinese font; no external calls')
