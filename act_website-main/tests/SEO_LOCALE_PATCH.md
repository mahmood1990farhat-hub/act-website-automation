# Homepage metadata and airport locale links — prepared, not deployed

1 October 2026. Base main: 23a7e31bee5ff8cb539f973282ddc98f5f99a07d.
Branch: codex/seo-metadata-airport-links-20261001.

Changes: English/Arabic homepage title and description; all five airport pages
now derive booking/contact links and Service schema URLs from the route locale.
The contact destination is the existing /{locale}/about-us#contact-us form;
booking remains /{locale}#book-now. Airport page components become async to
resolve their existing Promise-based locale params. Canonical/hreflang helper,
booking logic, contact form, pricing and authentication are unchanged.

Fourteen source-contract checks passed using Python stdlib:

```sh
python -m unittest discover -s act_website-main/tests -p test_seo_locale_patch.py -v
```

These verify source contracts and existing anchor destinations, not rendered HTML,
HTTP responses, TypeScript compilation or a production Next.js build. Full frontend
dependencies are not installed in the authoring workspace. Before release, run
the normal frontend build and rendered metadata/CTA checks for both locales.
No new hosted workflow was created and no production main push was performed.

Airport body copy, airport titles and CTA labels remain English as in the base;
full airport translation is deliberately a separate scoped task. Arabic homepage
copy is authored here and has not received independent language review. Sitemap
lastmod and business-claim verification remain in the SEO backlog.

Do not merge automatically: any website main push triggers frontend production
deployment. Next task: verify this exact patch with a frontend build and rendered
English/Arabic metadata and link checks, then review release separately.
