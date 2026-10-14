"use client";

import { FormEvent, useState } from "react";

export type VehicleHistory = {
  id: number; registration: string; make: string; model: string;
  colour: string; class_code: string; keeper_name: string; keeper_address: string;
  available_from: string; ceased_at: string | null; close_reason: string;
  evidence: { id: number; kind: string; name: string; download_endpoint: string }[];
};
export type OperatorRecord = {
  national_insurance_recorded: boolean;
  registered_keeper_name: string; registered_keeper_address: string;
  driver_available_from: string | null; driver_ceased_available_on: string | null;
  vehicle_available_from: string | null; vehicle_ceased_available_on: string | null;
  is_currently_available: boolean;
};
type Evidence = { id: number; kind: string; name: string; download_endpoint: string };

export default function UnifiedDriverLifecycle({
  applicationId, token, operatorRecord, vehicleHistory, onChanged, onDownload,
}: {
  applicationId: number; token: string; operatorRecord: OperatorRecord;
  vehicleHistory: VehicleHistory[]; onChanged: () => void;
  onDownload: (file: Evidence) => Promise<void>;
}) {
  const [showReplacement, setShowReplacement] = useState(false);
  const [ownership, setOwnership] = useState("phv_owner");
  const [ceaseReason, setCeaseReason] = useState("");
  const [ceaseConfirmed, setCeaseConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const api = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  const control = "mt-1 w-full rounded-lg border border-gray-300 p-2 font-normal text-gray-900";
  const acceptedFiles = "application/pdf,image/jpeg,image/png";
  const formatDate = (v: string | null | undefined) => v ? new Date(v).toLocaleDateString("en-GB") : "—";
  // Temporary account suspension is not a permanent end to the operator period.
  const canCease = !!operatorRecord.driver_available_from && !operatorRecord.driver_ceased_available_on;

  const submit = async (endpoint: string, body: BodyInit, type?: string) => {
    const headers: Record<string, string> = { Authorization: "Bearer " + token };
    if (type) headers["Content-Type"] = type;
    const response = await fetch(api + endpoint, {
      method: "POST", headers, body, cache: "no-store",
    });
    const result = await response.json();
    if (!response.ok) {
      const details = typeof result?.detail === "string" ? result.detail :
        Object.entries(result || {}).map(([k, v]) => k + ": " + String(v)).join("; ");
      throw new Error(details || "ACT could not save this operator record.");
    }
    onChanged();
  };

  const replaceVehicle = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || !operatorRecord.is_currently_available || !token) return;
    setBusy(true); setError("");
    try {
      await submit(
        "/api/drivers/admin/unified-applications/" + applicationId + "/replace-vehicle/",
        new FormData(event.currentTarget),
      );
    } catch (err: any) {
      setError(err?.message || "Vehicle replacement was denied.");
    } finally { setBusy(false); }
  };

  const ceaseAvailability = async () => {
    if (busy || !token || !canCease ||
        !ceaseConfirmed || ceaseReason.trim().length < 8) {
      setError("Confirm assignment review and provide a reason.");
      return;
    }
    if (!window.confirm("End this driver's ACT availability? No bookings will be reassigned or cancelled automatically.")) return;
    setBusy(true); setError("");
    try {
      await submit(
        "/api/drivers/admin/unified-applications/" + applicationId + "/cease/",
        JSON.stringify({ reason: ceaseReason.trim(), confirmed_no_outstanding_trips: true }),
        "application/json",
      );
    } catch (err: any) {
      setError(err?.message || "Unable to end availability.");
    } finally { setBusy(false); }
  };

  return <section className="mt-4 rounded-lg border p-4 text-sm">
    <h3 className="font-bold">TfL operator register — availability and vehicle history</h3>
    <p>Driver available from: {formatDate(operatorRecord.driver_available_from)}</p>
    <p>Driver ceased: {formatDate(operatorRecord.driver_ceased_available_on)}</p>
    <p>National Insurance: {operatorRecord.national_insurance_recorded ? "Recorded securely" : "Not recorded"} (number not displayed)</p>
    <div className="mt-3 space-y-3">
      {vehicleHistory.map(record => <div className="rounded-lg border p-3" key={record.id}>
        <p className="font-semibold">{record.registration} — {record.make} {record.model}</p>
        <p>Class: {record.class_code}. Colour: {record.colour}</p>
        <p>Registered keeper: {record.keeper_name}, {record.keeper_address}</p>
        <p>Available: {formatDate(record.available_from)} to {record.ceased_at ? formatDate(record.ceased_at) : "present"}</p>
        {record.close_reason && <p>Closure reason: {record.close_reason}</p>}
        <div className="mt-2 flex flex-wrap gap-2">
          {record.evidence.map(file => <button key={file.id} type="button"
            className="rounded border px-2 py-1 text-xs" disabled={busy}
            onClick={() => onDownload(file)}>Private {file.kind.replace(/_/g, " ")}</button>)}
        </div>
      </div>)}
    </div>

    {canCease && <>
      <div className="mt-4 border-t pt-3">
        {!operatorRecord.is_currently_available && <p className="mb-2 text-gray-600">
          Vehicle replacement is disabled while this account is unavailable. Permanent cessation remains available.
        </p>}
        <button type="button" className="rounded border px-3 py-2 font-semibold disabled:opacity-40"
          disabled={!operatorRecord.is_currently_available || busy}
          onClick={() => setShowReplacement(v => !v)}>
          {showReplacement ? "Close vehicle replacement" : "Replace verified vehicle"}
        </button>
        {showReplacement && operatorRecord.is_currently_available && <form onSubmit={replaceVehicle}
          className="mt-3 grid gap-3 rounded border p-3 sm:grid-cols-2">
          <p className="sm:col-span-2">
            Inspect genuine vehicle and keeper evidence. The old vehicle and documents remain in the history.
            No replacement is allowed with outstanding assigned trips.
          </p>
          <label>Vehicle ownership
            <select name="vehicle_ownership" value={ownership} required className={control}
              onChange={event => setOwnership(event.target.value)}>
              <option value="phv_owner">Owned licensed PHV</option>
              <option value="hiring_a_phv">Hired licensed PHV</option>
              <option value="other">Other authorised use</option>
            </select>
          </label>
          <label>ACT vehicle class
            <select name="vehicle_class_code" required className={control}>
              <option value="comfort">Comfort</option>
              <option value="comfort_xl">Comfort XL</option>
              <option value="executive">Executive</option>
              <option value="executive_xl">Executive XL</option>
              <option value="first_class">First Class</option>
            </select>
          </label>
          <label>Make <input name="vehicle_make" required className={control} /></label>
          <label>Model <input name="vehicle_model" required className={control} /></label>
          <label>Year <input type="number" name="vehicle_year" min="2015"
            max={new Date().getFullYear()} required className={control} /></label>
          <label>Registration <input name="vehicle_registration" required className={control} /></label>
          <label>Colour <input name="vehicle_colour" required className={control} /></label>
          <label>Pets permitted?
            <select name="accepts_pets" required className={control}>
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </label>
          <label>MOT expiry <input type="date" name="mot_expiry" required className={control} /></label>
          <label>Insurance expiry <input type="date" name="insurance_expiry" required className={control} /></label>
          <label>Registered keeper name
            <input name="registered_keeper_name" autoComplete="off" required className={control} />
          </label>
          <label>Registered keeper address
            <textarea name="registered_keeper_address" required className={control} />
          </label>
          {ownership === "other" && <label className="sm:col-span-2">Lawful-use explanation
            <textarea name="ownership_explanation" required className={control} />
          </label>}
          <label>MOT certificate <input type="file" name="mot" required accept={acceptedFiles} className={control} /></label>
          <label>Insurance evidence <input type="file" name="insurance" required accept={acceptedFiles} className={control} /></label>
          <label>PHV licence <input type="file" name="vehicle_phv" required accept={acceptedFiles} className={control} /></label>
          {(ownership === "phv_owner" || ownership === "other") && <label>V5C
            <input type="file" name="v5c" required={ownership === "phv_owner"} accept={acceptedFiles} className={control} />
          </label>}
          {(ownership === "hiring_a_phv" || ownership === "other") && <label>Hire/right-to-use evidence
            <input type="file" name="hire_agreement" required={ownership === "hiring_a_phv"} accept={acceptedFiles} className={control} />
          </label>}
          <label className="sm:col-span-2">Reason for replacement
            <textarea name="replacement_reason" minLength={8} maxLength={450} required className={control} />
          </label>
          <label className="flex gap-2 sm:col-span-2">
            <input name="documents_reviewed" type="checkbox" required />
            I inspected all required vehicle documents and eligibility.
          </label>
          <label className="flex gap-2 sm:col-span-2">
            <input name="operator_records_checked" type="checkbox" required />
            I verified the registered keeper's details.
          </label>
          <button type="submit" disabled={busy}
            className="rounded bg-gray-900 p-3 font-semibold text-white sm:col-span-2 disabled:opacity-40">
            {busy ? "Saving..." : "Confirm vehicle replacement"}
          </button>
        </form>}
      </div>
      <div className="mt-4 space-y-2 border-t pt-3">
        <h4 className="font-bold text-red-700">End driver availability</h4>
        <p>Ending availability is refused while trips are assigned. No automatic cancellations or reassignments occur.</p>
        <textarea aria-label="Reason for ceasing driver availability" className={control}
          value={ceaseReason} onChange={event => setCeaseReason(event.target.value)}
          placeholder="Reason (at least 8 characters)" minLength={8} maxLength={450} />
        <label className="flex gap-2">
          <input type="checkbox" checked={ceaseConfirmed}
            onChange={event => setCeaseConfirmed(event.target.checked)} />
          I have reviewed all current assignments and acknowledge the trip safety check.
        </label>
        <button type="button" disabled={busy || !ceaseConfirmed || ceaseReason.trim().length < 8}
          onClick={ceaseAvailability}
          className="rounded border border-red-600 px-3 py-2 font-semibold text-red-700 disabled:opacity-40">
          End ACT availability
        </button>
      </div>
    </>}
    {error && <p role="alert" className="mt-3 rounded bg-red-100 p-3 text-red-800">{error}</p>}
  </section>;
}
