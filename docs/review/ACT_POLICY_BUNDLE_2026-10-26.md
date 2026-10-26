# Policy documents and checkout references: matched review bundle

## Preserved baselines
Frontend PR #112 `4e469cf93327d89d7e28a09cd8ef3cc96b011f8a` and its 28-case browser result were read before this change. Backend dependency PR #111 stays at `c317a27b8ca663d296c7b241ed701371c69e2c77`. Policy PR #101 stays at `5618d56e111510e7cd1e32ecf524f67c34bcd9b7`.

The two original v0.2 Markdown sources are copied to their existing paths using the original Git blobs `4d95d04461f948754f72e267bea362c04c6ed513` (customer) and `2fcdc33f07c358fd73f4191e1d2f56c431366825` (driver). This is a pinned cross-branch source inclusion, not a rewrite, merge or legal sign-off. The new customer 24h/12h schedule is authoritative for this review; the older three-hour cancellation reference in the driver pack's historical implementation notes is NOT a current release instruction. The independent three-hour booking lead time remains intact.

## Implemented preparation
The existing `scripts/build-customer-documents.py` gets an explicit `--review-bundle` mode; removing that dispatch recovers its exact original blob `e827bc25d332e7b227d5c434efcb2b79d57cebf3`. No-argument legacy generation is not run by this change. The focused companion uses the existing WeasyPrint/source-to-PDF/hash approach, with no external resources, provider access or alternate mail/PDF service.

One input manifest pins source hashes and exact section boundaries. Three documents are generated: customer booking terms, driver application terms, and driver application/verification privacy. Only Markdown presentation and paragraph whitespace are normalised; policy words, order, qualifications, self-employed/HMRC clause, loss safeguard and unresolved publication notes are retained. Complete original source/reference registers are bundled, with no new legal assessment represented.

The canonical text feeds both a readable PDF/HTML review and `checkout-release.candidate.json`. Actual generated PDF bytes are hashed; the proposed versioned file URL maps to that exact local file. An index and separate driver/customer link map prevent driver terms or driver privacy being substituted for passenger documents. This is local artifact consistency, NOT independent verification of a live URL, source authenticity by signature or legal compliance.

All outputs are REVIEW ONLY. The candidate is `published:false`, has no effective date, and is not wired into runtime settings or form links. The tool refuses publication flags, output under repository website public paths, existing output, mismatched sources, unsafe/symlink paths and inconsistent bundle contents. The index exposes all remaining publication holds. A full source and each generated asset have hashes; the manifest is an integrity inventory, not a cryptographic signature or an authorisation token.

No translations are invented. Arabic is explicitly missing for the enabled English/Arabic checkout, and customer privacy remains separate/unfinalised. No automatic English fallback, hidden-language activation, new document approval or public-policy upload occurs. Existing public files/dictionaries/FAQs still require the separately approved final publication pass.

## Run in an isolated source checkout only

```bash
python act_website-main/scripts/build-customer-documents.py \
  --review-bundle docs/policy-releases/act-policy-review-20261026.json \
  --output /tmp/act-policy-review-new
python act_website-main/scripts/build-customer-documents.py \
  --verify-review-bundle /tmp/act-policy-review-new
```

Output must not already exist. These are build/review instructions, not VPS or deployment commands. No production configuration is to be loaded from this package.

## Verification boundary
Sixteen focused local tests passed after correcting a test-runner repository path. They include actual PDF generation and extracted-text parity for all canonical words in order, exact source preservation, source/path/mapping/hash rejection and disabled output. Local tools: Python 3.13, WeasyPrint 68.0, PyMuPDF 1.26.7. All 11 pages of the local three-document review set were rendered and visually inspected; no clipped text or replacement glyphs observed. Hosted workflow result is pending until the actual run and artifact are inspected. No prior booking, driver, checkout, refund, admin or email/PDF acceptance suite was rerun.

These tests validate the preparation code, not live PDF hosting, translated legal text, publication approval or combined website/backend acceptance. No existing confirmation/cancellation email, PDF template, stored journey PDF, booking, refund, schema or migration changes. No production setting, provider subscription, staff permission, n8n workflow or native app changes. Preserve all prior branches/revisions and test evidence. Separate exact-revision deployment approval remains required.

## Remaining publication work, kept finite
Company/operator particulars and operational/fairness facts remain to be confirmed; driver DBS/supplier/retention processing facts remain marked unresolved. Produce reviewed Arabic documents and the distinct customer privacy final text. Then align public dictionaries/FAQs, versioned downloadable files and customer/driver links, verify actual served hashes, and perform combined release acceptance. Existing exception-support work remains a separate unfinished part of #99. This bundle does not claim to close any of those issues.
