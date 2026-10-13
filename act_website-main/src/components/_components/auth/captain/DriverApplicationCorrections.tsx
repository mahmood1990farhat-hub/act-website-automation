"use client";

import { useState } from "react";

const docKinds = new Set([
  "pco_front", "pco_back", "dvla_front", "dvla_back", "driver_photo",
  "mot", "insurance", "v5c", "vehicle_phv", "hire_agreement", "dbs",
]);
const dateKinds = new Set(["pco_badge_expiry", "mot_expiry", "insurance_expiry"]);
const knownKinds = new Set([
  ...docKinds, ...dateKinds,
  "pco_badge_number", "vehicle_registration", "vehicle_colour",
  "vehicle_make", "vehicle_model", "vehicle_year",
]);
const className = "mt-1 block w-full rounded-lg border border-gray-400 bg-white p-3 text-black";

export default function DriverApplicationCorrections({
  token, requested, reason,
}: {
  token: string;
  requested: string[];
  reason?: string;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [files, setFiles] = useState<Record<string, File | undefined>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [completed, setCompleted] = useState(false);

  const kinds = requested.filter(x => knownKinds.has(x));
  const update = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy || completed) return;
    if (kinds.length !== requested.length) {
      setMessage("This request includes an unsupported field. Contact ACT support.");
      return;
    }
    const body = new FormData();
    for (const kind of kinds) {
      if (docKinds.has(kind)) {
        if (!files[kind]) {
          setMessage("Upload the requested " + kind.replace(/_/g, " ") + " document.");
          return;
        }
        body.append(kind, files[kind]!);
      } else {
        if (!values[kind]?.trim()) {
          setMessage("Correct the requested " + kind.replace(/_/g, " ") + " field.");
          return;
        }
        body.append(kind, values[kind].trim());
      }
    }
    setBusy(true); setMessage("");
    try {
      const response = await fetch(
        (process.env.NEXT_PUBLIC_API_BASE_URL || "") + "/api/drivers/onboarding/correct/",
        { method: "POST", headers: { Authorization: `Bearer ${token}` }, body },
      );
      const result = await response.json();
      if (!response.ok) {
        throw new Error(String(result?.detail ||
          Object.entries(result).map(([key, value]) => key + ": " + String(value)).join("; ") ||
          "Corrections were not accepted."));
      }
      setCompleted(true);
      setMessage("Corrections received. ACT will review your application again.");
    } catch (error: any) {
      setMessage(error?.message || "Unable to submit corrections.");
    } finally {
      setBusy(false);
    }
  };

  if (!kinds.length) return <p className="mt-4 text-sm">
    No corrections have been specified. Please contact ACT support before reapplying.
  </p>;

  return <section className="mt-5 rounded-xl border border-yellow-500/70 bg-gray-800 p-4 text-white">
    <h2 className="text-xl font-bold text-yellow-400">Application corrections requested</h2>
    {reason && <p className="mt-2 text-sm">ACT reviewer note: {reason}</p>}
    {completed ? <p role="status" className="mt-4 rounded bg-green-900/50 p-3">{message}</p> :
      <form onSubmit={update} className="mt-4 space-y-4">
        {kinds.map(kind => <label key={kind} className="block text-sm font-semibold">
          {kind.replace(/_/g, " ")} *
          {docKinds.has(kind) ? (
            <input type="file" required className="mt-2 block w-full"
              accept={kind === "driver_photo" ? "image/png,image/jpeg" : ".pdf,image/png,image/jpeg"}
              onChange={event => setFiles(old => ({ ...old, [kind]: event.target.files?.[0] }))} />
          ) : (
            <input type={dateKinds.has(kind) ? "date" : kind === "vehicle_year" ? "number" : "text"}
              required className={className} value={values[kind] || ""}
              onChange={event => setValues(old => ({ ...old, [kind]: event.target.value }))} />
          )}
        </label>)}
        {message && <p role="alert" className="rounded bg-red-900/40 p-3 text-sm">{message}</p>}
        <button disabled={busy}
          className="w-full rounded-lg bg-yellow-400 p-3 font-bold text-black disabled:opacity-50">
          {busy ? "Submitting corrections..." : "Submit requested corrections"}
        </button>
      </form>}
  </section>;
}
