# ACT TfL operator-register correction — UNTESTED DRAFT

## Baseline
This proposal is based on production-baseline scoped backend PR #94 at `c02fa3c5520c7d0e00f8d8d9653471d726d58bac`, rather than merging unrelated GitHub main changes. Complementary admin website-only input is proposed from scoped frontend PR #95. No production alteration or new applicant form submission.

## Source of obligations
Private Hire Vehicles (London) (Operators' Licences) Regulations 2000, regs 12–13 and 16:
https://www.legislation.gov.uk/uksi/2000/3146/made/data.html
TfL private hire operator handbook:
https://tfl.gov.uk/cdn/static/cms/documents/private-hire-operator-handbook.pdf

## Proposed approach
* ACT admin captures driver's National Insurance number (NI) and registered keeper's name/address at final approval, not during the public one-form application.
* NI is validated, then encrypted with Fernet under the mandatory `ACT_NI_ENCRYPTION_KEY` in a protected environment; no plaintext fallback, no public/admin-detail/plaintext API exposure. Never commit or disclose the key, and back up the key separately and securely.
* Approval cannot mark a unified applicant dispatch eligible until records and current document/DBS/photo checks pass.
* Separate driver/vehicle became-available dates are set upon actual approval. Nullable cessation dates are reserved for later lifecycle handling.

## Release STOP gates
1. Verify real server private root and Nginx isolation, backups/off-host secure restore and database migration plan for **0004–0006** (not just 0004–0005). New key must be provisioned and recoverable, with operational key rotation/inspection policy.
2. Implement/audit changes to driver cessation and vehicle changes to record separate ceased-availability dates. Current fields alone are not a complete operator record lifecycle; do not claim TfL compliance until it is finished.
3. Confirm authorized retrieval of NI for lawful inspection without broad disclosure; complete retention/disposal for required operator register records (12 months after cessation), distinct from unnecessary vetting copies.
4. Pair this backend candidate with reviewed frontend-only admin UI, focused affected tests and an isolated combined revalidation **of the new pair**.
5. Preserve legacy driver data and paid Trip #34; do not replay payments, modify published n8n, merge or deploy without owner approval.

**Status:** Draft code in a dedicated GitHub branch. Unmerged; untested until specific new acceptance evidence is recorded.
