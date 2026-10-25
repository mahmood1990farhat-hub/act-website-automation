"use client";

import React, { useEffect, useRef, useState } from "react";

type Row = { cancellation_id: string; trip_id: number; booking_reference: string;
  cancellation_received_at: string; refund_status: string; journey_status: string; has_hold: boolean };
type Detail = { operator_schema: number; cancellation_id: string; trip_id: number; booking_reference: string;
  status: string; cancellation_received_at: string; refund_status: string; accounting_status: string;
  captured_pence: number | null; currency: string; hold_reason: string; stopped_at: string;
  terms_evidence: string; terms: null | { terms_version: string; policy_version: string; locale: string;
    terms_sha256: string; accepted_at: string; pickup_at: string; terms_text: string };
  operation: null | { status: string; amount_pence: number; first_attempt_at: string | null;
    updated_at: string; accounting_posted: boolean };
  actions: { review: boolean; reconcile: boolean; reason: string }; read_at: string };
type Page = { page: number; page_size: number; count: number; has_next: boolean };
type Envelope<T> = { success: boolean; data: T; pagination?: Page };
type Confirmation = { caseId: string; pence: number; reference: string };

export function parseLossPence(raw: string): number | null {
  const value = raw.trim();
  if (!/^(0|[1-9][0-9]{0,7})(\.[0-9]{1,2})?$/.test(value)) return null;
  const [pounds, pennies = ""] = value.split(".");
  const result = Number(pounds) * 100 + Number(pennies.padEnd(2, "0"));
  return Number.isSafeInteger(result) ? result : null;
}

function money(pence: number | null | undefined) {
  return typeof pence === "number" && Number.isSafeInteger(pence) && pence >= 0
    ? new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(pence / 100)
    : "Not verified";
}
function moment(value?: string | null) {
  if (!value || Number.isNaN(Date.parse(value))) return "Not recorded";
  return new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/London", dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
function label(state: string) {
  const labels: Record<string, string> = { manual_review: "Needs review", prepared: "Prepared — not sent",
    in_flight: "Request in progress", pending: "Provider pending", requires_action: "Action required",
    succeeded: "Provider confirmed", failed: "Provider failed — review", canceled: "Provider cancelled — review",
    reconcile: "Reconciliation required", not_due: "No additional refund due", processed: "Posted",
    processed_ledger_error: "Accounting review required", not_applicable: "Not applicable" };
  return labels[state] || "Status requires review";
}
class ReviewError extends Error { constructor(message: string, public status = 0) { super(message); } }
async function api<T>(path: string, token: string, body?: object): Promise<Envelope<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), body ? 30000 : 20000);
  const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/$/, "");
  try {
    const response = await fetch(`${base}/api/payments/cancellations/${path}`, {
      method: body ? "POST" : "GET", cache: "no-store", credentials: "omit",
      headers: { Authorization: `Bearer ${token}`, ...(body ? { "Content-Type": "application/json" } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}), signal: controller.signal,
    });
    if (!response.ok) {
      const messages: Record<number, string> = { 401: "Your session has expired. Sign in again.",
        403: "Your account does not have cancellation-review permission.",
        404: "This case or the review service is not available. Do not use another refund route.",
        409: "The case changed or needs support review. Refresh its saved status; do not force a retry." };
      throw new ReviewError(messages[response.status] || "The review service could not complete this request.", response.status);
    }
    const result = await response.json();
    if (result?.success !== true || result.data === undefined) throw new ReviewError("The server returned an unrecognised response.");
    return result as Envelope<T>;
  } finally { clearTimeout(timer); }
}

export default function CancellationReviewDashboard({ token }: { token?: string }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [page, setPage] = useState(1);
  const [paging, setPaging] = useState<Page | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [reload, setReload] = useState(0);
  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selected, setSelected] = useState("");
  const selectedRef = useRef("");
  const sequence = useRef(0);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [denied, setDenied] = useState(!token);
  const [loss, setLoss] = useState("");
  const [reference, setReference] = useState("");
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [uncertain, setUncertain] = useState(false);

  function fail(err: unknown) {
    setError(err instanceof Error ? err.message : "The request could not be completed.");
    if (err instanceof ReviewError && [401, 403].includes(err.status)) {
      setDenied(true); setRows([]); setDetail(null); setConfirmation(null);
    }
  }
  useEffect(() => {
    let ignore = false;
    sequence.current++;
    selectedRef.current = ""; setSelected(""); setDetail(null); setConfirmation(null);
    setRows([]); setPaging(null); setDenied(!token); setError("");
    if (!token) return;
    setListLoading(true);
    const params = new URLSearchParams({ page: String(page), ...(filter ? { trip_id: filter } : {}) });
    api<Row[]>(`?${params}`, token).then(result => {
      if (ignore) return;
      if (!Array.isArray(result.data) || !result.pagination) throw new ReviewError("Unrecognised queue response.");
      setRows(result.data); setPaging(result.pagination);
    }).catch(err => { if (!ignore) fail(err); }).finally(() => { if (!ignore) setListLoading(false); });
    return () => { ignore = true; sequence.current++; };
  }, [token, page, filter, reload]);

  async function loadCase(id: string) {
    if (!token || denied) return;
    const current = ++sequence.current;
    setDetailLoading(true); setDetail(null); setConfirmation(null); setAcknowledged(false);
    try {
      const result = await api<Detail>(`${encodeURIComponent(id)}/review/`, token);
      if (current !== sequence.current || selectedRef.current !== id) return;
      if (result.data.operator_schema !== 1 || result.data.cancellation_id !== id) throw new ReviewError("The case response does not match the selected record.");
      setDetail(result.data);
    } catch (err) { if (current === sequence.current) fail(err); }
    finally { if (current === sequence.current) setDetailLoading(false); }
  }
  function choose(row: Row) {
    if (busyRef.current) return;
    selectedRef.current = row.cancellation_id; setSelected(row.cancellation_id);
    setLoss(""); setReference(""); setError(""); setNotice(""); setUncertain(false);
    void loadCase(row.cancellation_id);
  }
  function prepareReview(event: React.FormEvent) {
    event.preventDefault();
    if (!detail?.actions.review || busyRef.current || uncertain || denied) return;
    const pence = parseLossPence(loss), ref = reference.trim();
    if (pence === null || ref.length < 8 || ref.length > 200) {
      setError("Enter a non-negative GBP net loss with no more than two decimal places and an evidence reference of 8–200 characters."); return;
    }
    setError(""); setAcknowledged(false);
    setConfirmation({ caseId: detail.cancellation_id, pence, reference: ref });
  }
  async function act(kind: "review" | "reconcile") {
    if (!token || !detail || busyRef.current || denied || detailLoading) return;
    if (kind === "review" && (!detail.actions.review || uncertain || !acknowledged || !confirmation || confirmation.caseId !== selected)) return;
    if (kind === "reconcile" && !detail.actions.reconcile) return;
    const id = selected;
    const body = kind === "review" ? { reviewed_net_loss_pence: confirmation!.pence, review_reference: confirmation!.reference } : {};
    busyRef.current = true; setBusy(true); setError(""); setNotice(""); setConfirmation(null);
    try {
      await api(`${encodeURIComponent(id)}/${kind}/`, token, body);
      setNotice(kind === "review" ? "Review request returned. Read the current saved outcome below; this is not a bank-credit confirmation." : "Provider-status check returned. No new refund was requested by this action.");
      await loadCase(id);
    } catch (err) {
      setUncertain(true); fail(err);
      setNotice("The outcome of this request may be uncertain. Do not resubmit a refund review. Refresh saved status and use reconciliation or ACT support.");
      await loadCase(id);
    } finally { busyRef.current = false; setBusy(false); }
  }

  return <section className="act-refund-review" lang="en" dir="ltr">
    <style>{`.act-refund-review{color:#e5e7eb;max-width:1280px;margin:auto;padding:24px;font:15px/1.55 Arial,sans-serif}.act-refund-review *{box-sizing:border-box}.act-refund-review h1{font-size:28px;margin:0 0 8px;color:#fff}.act-refund-review h2{font-size:20px;color:#fff;margin:0 0 14px}.act-refund-review h3{font-size:16px;margin:18px 0 8px}.act-refund-review p{margin:8px 0}.act-refund-review .muted{color:#b3becd}.act-refund-review .grid{display:grid;grid-template-columns:minmax(260px,1fr) minmax(0,2fr);gap:20px;margin-top:22px}.act-refund-review .card{background:#172131;border:1px solid #3c4758;border-radius:12px;padding:20px;min-width:0}.act-refund-review button{min-height:44px;border:1px solid #657083;border-radius:7px;padding:10px 14px;background:#253248;color:#fff;cursor:pointer;font:inherit}.act-refund-review button:disabled{opacity:.5;cursor:not-allowed}.act-refund-review .primary{background:#e3b66c;color:#172131;border-color:#e3b66c;font-weight:bold}.act-refund-review input{width:100%;padding:11px;background:#0c1422;color:#fff;border:1px solid #657083;border-radius:6px;font:inherit}.act-refund-review input[type=checkbox]{width:20px;height:20px;flex-shrink:0}.act-refund-review label{display:block;margin:12px 0}.act-refund-review .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.act-refund-review .case{display:block;width:100%;text-align:left;margin:10px 0;overflow-wrap:anywhere}.act-refund-review .case[aria-pressed=true]{border:2px solid #e3b66c}.act-refund-review .badge{display:inline-block;border:1px solid #657083;border-radius:20px;font-size:12px;padding:3px 10px;margin-top:7px}.act-refund-review .alert{padding:14px;border-radius:8px;background:#422c1b;border:1px solid #d6a456;overflow-wrap:anywhere}.act-refund-review .info{padding:14px;border-left:3px solid #e3b66c;background:#101b2b;margin:14px 0}.act-refund-review dl{display:grid;grid-template-columns:minmax(125px,1fr) minmax(0,2fr);gap:8px 18px}.act-refund-review dt{color:#b3becd}.act-refund-review dd{margin:0;overflow-wrap:anywhere}.act-refund-review pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit;max-height:250px;overflow:auto}.act-refund-review summary{cursor:pointer;min-height:44px}.act-refund-review .confirm{border:2px solid #e3b66c;padding:18px;border-radius:8px;margin-top:18px}.act-refund-review :focus-visible{outline:3px solid #ffcf80;outline-offset:3px}@media(max-width:800px){.act-refund-review{padding:14px}.act-refund-review .grid{grid-template-columns:1fr}.act-refund-review .card{padding:16px}.act-refund-review dl{grid-template-columns:1fr}.act-refund-review dd{margin-bottom:8px}}`}</style>
    <h1>Cancellation &amp; refund review</h1>
    <p className="muted">Review recorded booking terms and cancellation evidence. Opening a case never issues a refund.</p>
    {error && <p role="alert" className="alert">{error}</p>}
    {notice && <p role="status" className="info">{notice}</p>}
    {denied ? <p className="alert">An authorised staff session with cancellation-review permission is required. Sign in through the existing admin login.</p> : <div className="grid">
      <aside className="card" aria-label="Cancellation cases">
        <h2>Cancellation cases</h2>
        <form onSubmit={event => { event.preventDefault(); if(busyRef.current)return; if(search && !/^[1-9][0-9]{0,14}$/.test(search.trim())) { setError("Enter a numeric trip ID."); return; } setPage(1); setFilter(search.trim()); setReload(x=>x+1); }}>
          <label>Trip ID (optional)<input value={search} inputMode="numeric" onChange={e=>setSearch(e.target.value)} disabled={busy} /></label>
          <button type="submit" disabled={busy || listLoading}>Find cases</button>
        </form>
        {listLoading ? <p role="status">Loading cases…</p> : rows.length ? rows.map(row=><button key={row.cancellation_id} className="case" type="button" aria-pressed={selected===row.cancellation_id} onClick={()=>choose(row)} disabled={busy}>
          <strong>{row.booking_reference}</strong><br/><span className="muted">Received {moment(row.cancellation_received_at)} (UK)</span><br/>
          <span className="badge">{label(row.refund_status)}{row.has_hold ? " · Held" : ""}</span>
        </button>) : <p>No managed cancellation cases found. This is not proof that no historic cancellation exists.</p>}
        {paging && <div className="row"><button type="button" disabled={busy || page===1 || listLoading} onClick={()=>setPage(x=>x-1)}>Previous</button><span>Page {page}</span><button type="button" disabled={busy || !paging.has_next || listLoading} onClick={()=>setPage(x=>x+1)}>Next</button></div>}
      </aside>
      <main className="card" aria-label="Selected cancellation">
        {detailLoading ? <p role="status">Loading saved case…</p> : !detail ? <p>Select a case to inspect its recorded terms and status.</p> : <>
          <div className="row"><h2>{detail.booking_reference}</h2><span className="badge">{label(detail.refund_status)}</span></div>
          <p className="muted">Saved ACT state, not a fresh provider query. Times below are UK local time.</p>
          <dl><dt>Cancellation received</dt><dd>{moment(detail.cancellation_received_at)}</dd><dt>Journey stopped</dt><dd>{moment(detail.stopped_at)}</dd>
            <dt>Captured amount</dt><dd>{money(detail.captured_pence)}</dd><dt>Accepted terms</dt><dd>{detail.terms?.terms_version || "Unknown — support review required"}</dd>
            <dt>Terms language</dt><dd>{detail.terms?.locale || "Unknown"}</dd><dt>Acceptance recorded</dt><dd>{moment(detail.terms?.accepted_at)}</dd>
            <dt>Confirmed pickup</dt><dd>{moment(detail.terms?.pickup_at)}</dd><dt>Accounting status</dt><dd>{label(detail.accounting_status)}</dd>
            {detail.operation && <><dt>This refund operation</dt><dd>{money(detail.operation.amount_pence)} · {label(detail.operation.status)}</dd><dt>Accounting entry</dt><dd>{detail.operation.accounting_posted ? "Recorded" : "Not recorded / needs review"}</dd></>}
          </dl>
          {detail.terms && <details><summary>View the recorded terms</summary><p className="muted">Version shown is the version stored for this booking, not today’s policy.</p><pre>{detail.terms.terms_text}</pre></details>}
          <p className="info">{detail.actions.reason}</p>
          {detail.hold_reason && <p className="alert">Hold: {detail.hold_reason.replaceAll("_", " ")}</p>}
          <div className="row"><button type="button" disabled={busy} onClick={()=>{setError(""); void loadCase(selected);}}>Refresh saved status</button>
            {detail.actions.reconcile && <button type="button" disabled={busy} onClick={()=>void act("reconcile")}>Check provider status — no new refund</button>}
          </div>
          {detail.actions.review && !uncertain && <form onSubmit={prepareReview}>
            <h3>Review evidenced cancellation loss</h3>
            <p className="muted">Enter net loss after saved costs and replacement work. This is not a chosen refund amount. Do not paste personal documents or card details.</p>
            <label>Reviewed net loss (GBP)<input inputMode="decimal" autoComplete="off" value={loss} onChange={e=>{setLoss(e.target.value);setConfirmation(null);}} disabled={busy} /></label>
            <label>Evidence / case reference<input autoComplete="off" maxLength={200} value={reference} onChange={e=>{setReference(e.target.value);setConfirmation(null);}} disabled={busy} /></label>
            <button type="submit" disabled={busy} className="primary">Review entered details</button>
          </form>}
          {confirmation && <section className="confirm" aria-label="Confirm refund review"><h3>Confirm review</h3>
            <p>Booking: <strong>{detail.booking_reference}</strong><br/>Reviewed net loss: <strong>{money(confirmation.pence)}</strong><br/>Evidence reference: {confirmation.reference}</p>
            <p>The server applies the booked terms and safeguards. Confirming may issue a real refund once the coordinated release is enabled. A zero loss is not a zero-refund instruction.</p>
            <label className="row"><input type="checkbox" checked={acknowledged} onChange={e=>setAcknowledged(e.target.checked)} disabled={busy}/><span>I have reviewed the evidence and understand this may issue a refund.</span></label>
            <div className="row"><button type="button" disabled={busy || !acknowledged} className="primary" onClick={()=>void act("review")}>Confirm review and process refund</button><button type="button" disabled={busy} onClick={()=>setConfirmation(null)}>Back to editing</button></div>
          </section>}
          {uncertain && <p className="alert">Review submission is locked for this visit after an uncertain response. Inspect saved status and contact support; do not use a second refund route.</p>}
          <p className="muted">No email/PDF resend or direct Stripe refund button is provided here. Provider confirmation does not prove arrival in the customer’s bank.</p>
        </>}
      </main>
    </div>}
  </section>;
}
