/** Exact public contract from backend PR #111. Never infer legacy mode on failure. */
import type { Locale } from "../../i18n.config";

export type TermsDocument = Readonly<{ schema: 1; enabled: true; terms_version: string;
  terms_sha256: string; locale: Locale; text: string; document_url: string;
  pdf_sha256: string; effective_at: string }>;
export type TermsDescriptor = TermsDocument | Readonly<{ schema: 1; enabled: false }>;
export type TermsAcknowledgement = { accepted: true; terms_version: string; terms_sha256: string; locale: Locale };
export type PreparedPayment = { client_secret: string; price_breakdown: { total_cost: number }; [key: string]: unknown };

export async function readCheckoutTerms(locale: Locale): Promise<TermsDescriptor> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 12000);
  try {
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    const response = await fetch(`${base}/api/payments/checkout-terms/?${new URLSearchParams({ locale })}`,
      { method: "GET", cache: "no-store", credentials: "omit", signal: controller.signal,
        headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("terms_unavailable");
    const value = await response.json();
    if (!value || value.schema !== 1 || typeof value.enabled !== "boolean") throw new Error("invalid_terms");
    if (value.enabled === false) {
      if (Object.keys(value).sort().join(",") !== "enabled,schema") throw new Error("invalid_disabled_terms");
      return Object.freeze({ schema: 1, enabled: false });
    }
    if (value.locale !== locale || typeof value.terms_version !== "string"
      || !value.terms_version.trim() || value.terms_version.length > 120 || /[\r\n]/.test(value.terms_version)
      || typeof value.text !== "string" || !value.text.trim()
      || typeof value.terms_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.terms_sha256)
      || typeof value.pdf_sha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.pdf_sha256)
      || typeof value.document_url !== "string" || !/^\/documents\/[A-Za-z0-9/_-]+\.pdf$/.test(value.document_url)
      || value.document_url.includes("//") || typeof value.effective_at !== "string"
      || !Number.isFinite(Date.parse(value.effective_at))) throw new Error("invalid_terms");
    const bytes = new TextEncoder().encode(value.text);
    if (bytes.length > 262144) throw new Error("terms_too_large");
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
    if (hash !== value.terms_sha256) throw new Error("terms_hash_mismatch");
    // Allowlist only. The PDF digest is metadata, not proof of the hosted PDF bytes.
    return Object.freeze({ schema: 1, enabled: true, terms_version: value.terms_version,
      terms_sha256: hash, locale, text: value.text, document_url: value.document_url,
      pdf_sha256: value.pdf_sha256, effective_at: value.effective_at });
  } finally { window.clearTimeout(timeout); }
}

export function termsAcknowledgement(doc: TermsDescriptor): TermsAcknowledgement | undefined {
  return doc.enabled ? { accepted: true, terms_version: doc.terms_version,
    terms_sha256: doc.terms_sha256, locale: doc.locale } : undefined;
}

export function sameTerms(a: TermsDescriptor, b: TermsDescriptor): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function isPreparedPayment(value: unknown): value is PreparedPayment {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<PreparedPayment>;
  return typeof v.client_secret === "string" && /^pi_[A-Za-z0-9]+_secret_[A-Za-z0-9]+$/.test(v.client_secret)
    && typeof v.price_breakdown?.total_cost === "number"
    && Number.isFinite(v.price_breakdown.total_cost) && v.price_breakdown.total_cost > 0;
}
