# ACT Arabic policy translations — AR-01

**26 October 2026 | TRANSLATION REVIEW DRAFTS | NOT PUBLISHED, EFFECTIVE OR DEPLOYED**

The owner asked for Arabic versions of the three policy documents. These files are translations of the separated English v0.2 sections, not new commercial policies, a certified legal translation, or a translation of every internal implementation note. Original English text, qualifications, organisation and reference markers are preserved in meaning and order. No missing company/operator/supplier/DBS facts have been filled in, and no English-precedence clause is introduced.

## Authoritative sources checked before work

- English policy PR #101 at `5618d56e111510e7cd1e32ecf524f67c34bcd9b7`: customer source blob `4d95d04461f948754f72e267bea362c04c6ed513`; driver source blob `2fcdc33f07c358fd73f4191e1d2f56c431366825`.
- Separated review bundle PR #113 at `d368e8442007662c9fafef0e8fb2d89d56875be7`. Current head, recent PRs and its existing evidence record were inspected, not recreated.
- Existing downloaded English bundle ZIP independently SHA-256 checked: `da2770587be8969da2c4b3b64b537bce3983f56aa35083fda6338b9404212ce5`. Source hashes in that bundle match the pinned originals.

## Files and correspondence

| Arabic section source | English section | Aligned blocks | Arabic PDF pages |
| --- | --- | ---: | ---: |
| `customer-booking-terms-sections.md` | Customer pack Part A | 61 | 5 |
| `driver-application-terms-sections.md` | Driver pack Part A | 33 | 3 |
| `driver-privacy-notice-sections.md` | Driver pack Part B | 33 | 3 |

The 127 aligned blocks include headings, paragraphs and list items. Numbered headings, numeric references, email/telephone details and `[L…]` / `[S…]` markers were checked against the source. The reference registers remain in the complete original English sources included in the conversation review ZIP. Acronyms and official identifiers are retained, with Arabic explanations where needed; registered keeper is not changed into vehicle owner.

Key wording retained: >24 hours full refund; >12 through 24 hours 50%; <=12 hours no refund under the standard schedule; exact boundary wording; fair-loss/consumer-rights safeguard; the distinct three-hour booking lead time; ACT's own failure-to-supply remedy; intended exclusively self-employed model; applicable Self Assessment/HMRC responsibilities and statutory qualifications; initial acceptance versus final driving approval; rental evidence; and all privacy publication holds and retention distinctions.

## Document checks and review artifacts

Arabic review PDFs and editable Markdown/HTML were produced locally using WeasyPrint 68.0, with right-to-left Arabic layout and isolated Latin identifiers/numbers. All 11 final PDF pages were independently rasterised with Poppler and visually inspected; text bounding-box checks found no clipping beyond the selected margins, empty pages or replacement glyphs. A minor Arabic grammatical correction was made before the final artifacts. The numbered page footer was corrected to preserve page/total order.

The package includes an English/Arabic block-by-block HTML comparison, editable sources, original English reference sources, a provenance/hash manifest and SHA256SUMS. These checks establish document preparation and inspectable alignment, **not independent bilingual legal sign-off, semantic correctness proven by software, or application acceptance**. No previously completed application/financial/email/PDF test suite was rerun. No hosted CI success is claimed for this documentation-only translation.

Final translated section Git blobs (including the review-only HTML comment):
- Customer: `30e1258f6107b2b23b587a2c4dd3b755d190e0f2`.
- Driver terms: `9a95aa40f3aac2f2de5b620fa447a6ef77716579`.
- Driver privacy: `913f2cb1ccce15f0e616114fe4096e284b032c43`.

Conversation Arabic PDF SHA-256 values:
- Customer: `e271825a5f90330340c21812b2bcf6835d93dffe3ca8630ca0dd01bbe294e23e`.
- Driver terms: `f8c54205225e314e31701bae901fd618f20065c096c0f345723bc38228ce12cd`.
- Driver privacy: `a34305e6b8d707d2ea34de4dbbccabef3e63fd453cff8963c52b4f7cd0aa4675`.
- Complete `ACT_Arabic_Policy_Review_Pack_20261026.zip`: `dd9722c1c691a72ed6733761d9df29af652220479262767d772efc3d2d99cc70`.

The PDFs are conversation review attachments, not files committed to public website paths. No font files are shared. The body text in those artifacts matches these committed Arabic sections; the artifacts also carry explicit review-only titles, metadata and a source note.

## Release boundary and remaining work

Arabic drafts are now prepared and committed. They are **not approved for publication or wired into the English-only candidate manifest in PR #113**. That manifest must be extended deliberately after content review; do not merely toggle a locale or treat the existing generator as already supporting these files. No runtime release, public dictionary, FAQ, checkout URL, driver policy link, stored booking terms or feature flag has changed.

The separate customer privacy notice remains unfinished and is not replaced by driver privacy. Existing company/operator, cancellation-loss/operational, driver DBS, supplier/transfer and retention checks remain open in both languages. Final bilingual wording review, coordinated source/PDF/hash/link integration, combined acceptance and separate exact-revision deployment approval remain required. Existing working booking-confirmation/cancellation emails and PDFs, payments/refunds, backend, frontend, migrations, n8n and native apps are untouched. Keep issue #99 open.
