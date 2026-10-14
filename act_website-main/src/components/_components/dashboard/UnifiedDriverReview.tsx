"use client";

import { useEffect, useState } from "react";

type Review = {
  application_id: number;
  status: string;
  awaiting_vehicle: boolean;
  password_is_set: boolean;
  personal: Record<string, string>;
  licence: Record<string, string>;
  vehicle: Record<string, string | number | boolean | null>;
  operator_record?: {
    national_insurance_recorded: boolean;
    registered_keeper_name: string;
    registered_keeper_address: string;
    driver_available_from: string | null;
    driver_ceased_available_on: string | null;
    vehicle_available_from: string | null;
    vehicle_ceased_available_on: string | null;
  };
  documents: {
    id: number; kind: string; name: string; size: number;
    download_endpoint: string;
  }[];
};

const correctionOptions = [
  "pco_front", "pco_back", "dvla_front", "dvla_back", "driver_photo",
  "mot", "insurance", "v5c", "vehicle_phv", "hire_agreement", "dbs",
  "pco_badge_number", "pco_badge_expiry", "mot_expiry", "insurance_expiry",
  "vehicle_registration", "vehicle_colour", "vehicle_make", "vehicle_model",
  "vehicle_year",
];

export default function UnifiedDriverReview({
  applicationId, token, onClose, onDecision,
}: {
  applicationId: number;
  token?: string;
  onClose: () => void;
  onDecision: () => void;
}) {
  const [details, setDetails] = useState<Review | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [docsReviewed, setDocsReviewed] = useState(false);
  const [dbsCleared, setDbsCleared] = useState(false);
  const [photoConsent, setPhotoConsent] = useState(false);
  const [nationalInsurance, setNationalInsurance] = useState("");
  const [keeperName, setKeeperName] = useState("");
  const [keeperAddress, setKeeperAddress] = useState("");
  const [operatorRecordsChecked, setOperatorRecordsChecked] = useState(false);
  const [reason, setReason] = useState("");
  const [requestedCorrections, setRequestedCorrections] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const api = process.env.NEXT_PUBLIC_API_BASE_URL || "";

  useEffect(() => {
    // Never carry a previously entered NI/keeper record into another applicant.
    setNationalInsurance("");
    setKeeperName("");
    setKeeperAddress("");
    setOperatorRecordsChecked(false);
    const controller = new AbortController();
    const load = async () => {
      setLoading(true);
      if (!token) { setError("Admin login required."); setLoading(false); return; }
      try {
        const res = await fetch(
          api + `/api/drivers/admin/unified-applications/${applicationId}/`,
          { signal: controller.signal, cache: "no-store",
            headers: { Authorization: `Bearer ${token}` } },
        );
        if (!res.ok) throw new Error("Unable to read this application.");
        const data = await res.json();
        setDetails(data);
      } catch (err: any) {
        if (!controller.signal.aborted) setError(err?.message || "Unable to load.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [api, applicationId, token]);

  const download = async (fileItem: Review["documents"][number]) => {
    if (!token || busy) return;
    setBusy(true); setError("");
    try {
      const res = await fetch(api + fileItem.download_endpoint, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
      });
      if (!res.ok) throw new Error("Private evidence download was denied.");
      const blob = await res.blob();
      const temporaryUrl = URL.createObjectURL(blob);
      try {
        const anchor = document.createElement("a");
        anchor.href = temporaryUrl;
        anchor.download = fileItem.name || "driver-evidence";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      } finally {
        setTimeout(() => URL.revokeObjectURL(temporaryUrl), 1000);
      }
    } catch (e: any) {
      setError(e?.message || "Download failed.");
    } finally { setBusy(false); }
  };

  const decide = async (action: "approve" | "reject" | "request_changes") => {
    if (!token || busy || !details) return;
    if (action === "approve" && (!docsReviewed || !dbsCleared || !photoConsent)) {
      setError("Verify all documents, actual DBS clearance and permission to disclose the driver photo.");
      return;
    }
    if (action === "approve" &&
      (!nationalInsurance.trim() || !keeperName.trim() || !keeperAddress.trim() || !operatorRecordsChecked)) {
      setError("Enter and verify the TfL National Insurance and registered keeper records before approval.");
      return;
    }
    if (action !== "approve" && reason.trim().length < 8) {
      setError("Give a specific reason for rejection or required corrections.");
      return;
    }
    if (action === "request_changes" && requestedCorrections.length === 0) {
      setError("Select the exact missing or incorrect details.");
      return;
    }
    setBusy(true); setError("");
    try {
      const res = await fetch(
        api + `/api/drivers/admin/unified-applications/${applicationId}/decision/`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            action,
            reason,
            files_to_modify: action === "request_changes" ? requestedCorrections : undefined,
            documents_reviewed: docsReviewed,
            dbs_cleared: dbsCleared,
            photo_disclosure_consent: photoConsent,
            national_insurance_number: action === "approve" ? nationalInsurance : undefined,
            registered_keeper_name: action === "approve" ? keeperName : undefined,
            registered_keeper_address: action === "approve" ? keeperAddress : undefined,
            operator_records_checked: action === "approve" ? operatorRecordsChecked : undefined,
          }),
        },
      );
      const result = await res.json();
      if (!res.ok) throw new Error(
        String(result?.detail || Object.entries(result).map(
          ([key, value]) => key + ": " + String(value),
        ).join("; ") || "Decision failed."),
      );
      onDecision();
    } catch (err: any) {
      setError(err?.message || "The decision could not be saved.");
    } finally { setBusy(false); }
  };

  return <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/85 p-3">
    <div role="dialog" aria-modal="true" aria-label="Unified driver application review"
      className="max-h-[94vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-gray-300 bg-white p-5 text-gray-900 shadow-xl">
      <header className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold">Driver verification — #{applicationId}</h2>
        <button type="button" className="rounded border px-3 py-2" onClick={onClose}>Close</button>
      </header>
      {loading ? <p className="my-5">Loading private application…</p> : !details ? <p>Could not load application.</p> : <>
        <p className="mt-4 rounded-lg bg-gray-100 p-3 text-sm">
          Status: <strong>{details.status}</strong> — password set: {details.password_is_set ? "Yes" : "No"}
          {details.awaiting_vehicle && <span className="block text-red-600">
            No vehicle: approval for driver trip work is prohibited.
          </span>}
        </p>
        {(["personal", "licence", "vehicle"] as const).map(section =>
          <section key={section} className="mt-4 rounded-lg border p-4">
            <h3 className="mb-3 font-bold capitalize">{section}</h3>
            <dl className="grid gap-2 sm:grid-cols-2">
              {Object.entries(details[section]).map(([key, value]) =>
                <div key={key} className="min-w-0 text-sm">
                  <dt className="font-semibold text-gray-600">{key.replace(/_/g, " ")}</dt>
                  <dd className="break-words">{value == null || value === "" ? "—" : String(value)}</dd>
                </div>)}
            </dl>
          </section>,
        )}
        {details.operator_record?.national_insurance_recorded && <section className="mt-4 rounded-lg border p-4 text-sm">
          <h3 className="mb-2 font-bold">TfL operator register (restricted)</h3>
          <p>NI number: securely recorded (not displayed).</p>
          <p>Registered keeper: {details.operator_record.registered_keeper_name || "—"}</p>
          <p>Keeper address: {details.operator_record.registered_keeper_address || "—"}</p>
          <p>Driver available from: {details.operator_record.driver_available_from || "—"}</p>
          <p>Vehicle available from: {details.operator_record.vehicle_available_from || "—"}</p>
        </section>}
        <section className="mt-4 rounded-lg border p-4">
          <h3 className="font-bold">Private uploaded evidence</h3>
          <p className="my-2 text-xs text-gray-600">
            Documents are never public links. Download through your authorized admin session only.
          </p>
          <div className="space-y-2">
            {details.documents.map(file =>
              <div className="flex items-center justify-between gap-2 rounded bg-gray-100 p-2 text-sm" key={file.id}>
                <span className="break-words">{file.kind.replace(/_/g, " ")} — {file.name}</span>
                <button type="button" className="shrink-0 rounded border px-3 py-2"
                  disabled={busy} onClick={() => download(file)}>Download</button>
              </div>)}
          </div>
        </section>
        {details.status === "pending" && <section className="mt-4 space-y-3 border-t pt-4 text-sm">
          <h3 className="font-bold">Final ACT verification</h3>
          <label className="flex gap-3">
            <input type="checkbox" checked={docsReviewed} onChange={e => setDocsReviewed(e.target.checked)} />
            I have inspected the genuine identity, TfL/DVLA, insurance and vehicle documents.
          </label>
          <label className="flex gap-3">
            <input type="checkbox" checked={dbsCleared} onChange={e => setDbsCleared(e.target.checked)} />
            I have independently verified current DBS clearance.
          </label>
          <label className="flex gap-3">
            <input type="checkbox" checked={photoConsent} onChange={e => setPhotoConsent(e.target.checked)} />
            I confirmed consent to disclose this verified driver photo to ACT passengers.
          </label>
          <div className="space-y-3 rounded-lg border border-gray-300 p-3">
            <h4 className="font-semibold">TfL operator records — required before approval</h4>
            <p className="text-xs text-gray-600">
              Enter these only after inspecting genuine driver and keeper evidence.
              NI is encrypted in ACT records, never displayed to passengers.
            </p>
            <label className="block font-semibold">Driver National Insurance number
              <input type="text" autoComplete="off" autoCapitalize="characters"
                value={nationalInsurance} onChange={event => setNationalInsurance(event.target.value)}
                className="mt-1 w-full rounded-lg border p-2 font-normal" />
            </label>
            <label className="block font-semibold">Vehicle registered keeper name
              <input type="text" autoComplete="off" value={keeperName}
                onChange={event => setKeeperName(event.target.value)}
                className="mt-1 w-full rounded-lg border p-2 font-normal" />
            </label>
            <label className="block font-semibold">Vehicle registered keeper address
              <textarea value={keeperAddress} onChange={event => setKeeperAddress(event.target.value)}
                className="mt-1 w-full rounded-lg border p-2 font-normal" />
            </label>
            <label className="flex gap-3">
              <input type="checkbox" checked={operatorRecordsChecked}
                onChange={event => setOperatorRecordsChecked(event.target.checked)} />
              I verified the NI number and registered keeper details against their evidence.
            </label>
          </div>
          <button type="button" onClick={() => decide("approve")}
            disabled={busy || details.awaiting_vehicle || !details.password_is_set}
            className="w-full rounded-lg bg-green-700 p-3 font-semibold text-white disabled:opacity-40">
            Final approve (driver eligible only after confirmation)
          </button>
          <label className="block font-semibold">Reason for rejection or correction request
            <textarea className="mt-1 w-full rounded-lg border p-3" value={reason}
              onChange={e => setReason(e.target.value)} />
          </label>
          <div className="space-y-2 rounded-lg border border-yellow-600/50 p-3">
            <p className="font-semibold">Request specific corrections instead of rejecting</p>
            <p className="text-xs text-gray-600">
              Select only documents or details that are missing or incorrect. The applicant
              can replace them securely using the same account.
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {correctionOptions.map(kind => <label key={kind} className="flex gap-2 text-xs">
                <input type="checkbox" checked={requestedCorrections.includes(kind)}
                  onChange={event => setRequestedCorrections(previous =>
                    event.target.checked ? [...previous, kind] : previous.filter(item => item !== kind))} />
                {kind.replace(/_/g, " ")}
              </label>)}
            </div>
            <button type="button" disabled={busy} onClick={() => decide("request_changes")}
              className="w-full rounded-lg border border-yellow-700 p-3 font-semibold text-yellow-800 disabled:opacity-40">
              Request corrections
            </button>
          </div>
          <button type="button" onClick={() => decide("reject")} disabled={busy}
            className="w-full rounded-lg border border-red-600 p-3 font-semibold text-red-700 disabled:opacity-40">
            Reject application
          </button>
        </section>}
      </>}
      {error && <p role="alert" className="mt-4 rounded bg-red-100 p-3 text-sm text-red-800">{error}</p>}
    </div>
  </div>;
}
