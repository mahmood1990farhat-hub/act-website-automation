# English/Arabic document binding — review preparation only

## Owner requirement
English website pages should show English policy wording and English PDF links; Arabic pages should show the corresponding Arabic wording and Arabic PDF links. Use the page's explicitly selected language, not a guess based on IP, name or device. Both language versions remain separately addressable; this is a display-selection rule, not a prohibition on opening a direct document link.

Before payment preparation, a change of language requires fresh agreement to the matching text. PR #112 already contains this behaviour and its existing 28-case browser evidence; it is not recreated or rerun here. Once a payment has its accepted document, a page-language change must not silently rewrite that document or an existing booking's acceptance record. Do not resend historical emails or regenerate journey PDFs merely because the website language changes.

## Source and previous work preserved
Read current PRs #101/#113, latest open PRs, the exact branch head and existing test evidence before editing. Base document preparation is d368e8442007662c9fafef0e8fb2d89d56875be7. Arabic sources come from documentation head 103ca3fc09a249e8e566d2e8f1321f8bacc21972. Source copies reuse the same Git blobs; no policy wording, commercial rule, translation, source review note, company/operator fact or privacy hold is rewritten.

The original English generator module was reconstructed locally only after its exact blob f778944defd12c91a4c1eec083930367c3796ad1 was verified. Existing downloaded English and Arabic review packages match their previously recorded SHA-256 values. No repository access failure was treated as permission to guess a source or overwrite another branch.

## Added to the existing process
The existing review builder now supports explicitly paired en/ar sources, verifies each translation against the exact canonical English text hash, and generates six documents: customer terms, driver terms and driver privacy in each language. English canonical hashes remain unchanged. Versions are shared across each language pair; translated text and PDF bytes have separate hashes and paths.

New input: docs/policy-releases/act-policy-review-bilingual-20261026.json. The earlier English-only input and artifact remain preserved. The bilingual input requires all three language pairs. An English-only input continues to build an English-only review package; absence of Arabic is reported, not silently filled with English.

The checkout candidate now has explicit locales.en and locales.ar entries. The document-link map has separate language groups and no ambiguous global English URL. Exact-language selection rejects missing/unsupported languages and crossed PDF paths. Full-bundle verification rejects replacing Arabic checkout content or links with English even when a local file inventory is recomputed. These checks establish artifact consistency, not authenticity against a malicious author or legal approval.

Arabic HTML/PDF rendering uses right-to-left layout with isolated Latin identifiers and numbers. All source text is escaped. The English renderer/body text is unchanged. No font files are added or distributed. There is no new email/PDF service or alteration to working confirmation/cancellation templates.

## Evidence at commit preparation
Twelve new local checks passed using actual six-document rendering with outbound socket access blocked. Checks cover both language mappings, no fallback, unchanged English/source text, translation revision, duplicate/missing pairs, crossed links/text, escaped RTL output, nonempty PDFs and disabled release state. All 11 Arabic PDF pages were rasterised and visually inspected locally; text bounding boxes stayed within the inspected page margins. English PDFs retain their source and canonical content hashes. This is not independent bilingual legal sign-off or live browser testing.

The existing 16 document-builder tests are included in the hosted run because this change directly modifies their generator. The 12 new checks are added to that same workflow. Completed checkout, booking, driver, payment/refund, admin and email/PDF application suites are not rerun. Hosted results remain pending until the completed run and retained evidence are inspected.

## Approval and publication boundary
This is still a REVIEW-ONLY package: published=false, effective_at=null, runtime_wired=false. It is not loaded into Django settings, public dictionaries, FAQs, driver-policy links or live checkout. No merge or deployment is authorised by the owner's language clarification. No API key, real account, booking, refund, notification, migration, n8n or native-app change.

The Arabic drafts are now supported by the same preparation process as English. Remaining work is final bilingual content/publication review, separate customer privacy finalisation, unresolved company/operator and data-processing facts, actual approved public-file/form-link integration and combined release acceptance. Direct public PDF hashes and physical-device language switching still need their release checks. Keep issue #99 open and obtain separate exact-revision deployment approval.
