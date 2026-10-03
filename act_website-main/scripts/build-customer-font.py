#!/usr/bin/env python3
"""Rebuild the licensed ACT CJK subsets from current customer JSON catalogues. Requires fonttools[woff]."""
import json
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
import os
root=Path(__file__).resolve().parents[2]
text=''.join(p.read_text() for base in [root/'act_website-main/src',root/'act_backend-main/apps/trips/services',root/'act_backend-main/apps/accounts'] for p in base.rglob('*.json'))
text += (root/'act_website-main/node_modules/react-phone-number-input/locale/zh.json').read_text()
text += '客户年月日时分秒中国德国法国英国土耳其西班牙阿拉伯美国加拿大澳大利亚星期一二三四五六七八九十百千万零上午下午'
font=TTFont(os.environ['ACT_CJK_FONT']);options=subset.Options();options.layout_features=['*'];sub=subset.Subsetter(options=options);sub.populate(text=text);sub.subset(font)
for rec in font['name'].names:
 if rec.nameID in [1,4,6]:rec.string=('ACT Customer CJK' if rec.nameID!=6 else 'ACTCustomerCJK').encode(rec.getEncoding())
a=root/'act_backend-main/static/fonts';a.mkdir(exist_ok=True);font.save(a/'act-customer-cjk.otf')
b=root/'act_website-main/public/fonts';b.mkdir(exist_ok=True);font.flavor='woff2';font.save(b/'act-customer-cjk.woff2')
print('Bundled font sizes', (a/'act-customer-cjk.otf').stat().st_size,(b/'act-customer-cjk.woff2').stat().st_size)
