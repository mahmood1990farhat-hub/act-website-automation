"use client";

import { useState } from "react";

type VehicleKind = "mot" | "insurance" | "vehicle_phv" | "v5c" | "hire_agreement";
const baseInput = "mt-1 w-full rounded-lg border border-gray-300 bg-white p-3 text-gray-900";
const classes = [
  ["comfort", "Comfort Class"], ["comfort_xl", "Comfort XL"],
  ["executive", "Executive Class"], ["executive_xl", "Executive XL"],
  ["first_class", "First Class"],
];

export default function DriverVehicleSupplement({ token }: { token: string }) {
  const [ownership, setOwnership] = useState("phv_owner");
  const [fields, setFields] = useState<Record<string, string>>({
    vehicle_class_code: "", vehicle_make: "", vehicle_model: "",
    vehicle_year: "", vehicle_registration: "", vehicle_colour: "",
    mot_expiry: "", insurance_expiry: "", accepts_pets: "",
    ownership_explanation: "",
  });
  const [files, setFiles] = useState<Partial<Record<VehicleKind, File>>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [done, setDone] = useState(false);
  const set = (key: string, value: string) => setFields(v => ({ ...v, [key]: value }));

  const field = (key: string, label: string, type = "text") => (
    <label className="block text-sm font-medium" key={key}>{label} *
      <input type={type} className={baseInput} value={fields[key] || ""}
        onChange={e => set(key, e.target.value)} required />
    </label>
  );
  const upload = (key: VehicleKind, label: string, required: boolean) => (
    <label key={key} className="block text-sm font-medium">{label} {required ? "*" : "(optional)"}
      <input type="file" accept=".pdf,image/png,image/jpeg" required={required}
        className="mt-2 block w-full text-sm"
        onChange={e => setFiles(old => ({ ...old, [key]: e.target.files?.[0] }))} />
    </label>
  );
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy || done) return;
    setMessage("");
    const check = ("mot insurance vehicle_phv " + (ownership === "phv_owner" ? "v5c" :
        ownership === "hiring_a_phv" ? "hire_agreement" : "")).trim().split(" ") as VehicleKind[];
    if (check.some(k => !files[k])) {
      setMessage("Upload all required vehicle documents."); return;
    }
    if (ownership === "other" && (!fields.ownership_explanation.trim() ||
        (!files.v5c && !files.hire_agreement))) {
      setMessage("Explain your lawful vehicle use and upload V5C or hire proof."); return;
    }
    if (fields.accepts_pets !== "true" && fields.accepts_pets !== "false") {
      setMessage("Confirm whether you accept pets."); return;
    }
    setBusy(true);
    try {
      const data = new FormData();
      data.append("vehicle_ownership", ownership);
      for (const [key, value] of Object.entries(fields)) {
        if (value) data.append(key, value);
      }
      for (const [key, file] of Object.entries(files)) {
        if (file) data.append(key, file);
      }
      const response = await fetch(
        (process.env.NEXT_PUBLIC_API_BASE_URL || "") + "/api/drivers/onboarding/add-vehicle/",
        { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: data },
      );
      const result = await response.json();
      if (!response.ok) {
        throw new Error(String(result.detail || Object.entries(result).map(
          ([key, value]) => key + ": " + String(value),
        ).join("; ") || "Vehicle update was rejected."));
      }
      setDone(true);
      setMessage("Vehicle evidence received. ACT must inspect and approve it before you can receive bookings.");
    } catch (error: any) {
      setMessage(error?.message || "Unable to submit vehicle documents.");
    } finally {
      setBusy(false);
    }
  };

  return <section className="mt-6 rounded-xl border border-yellow-500/60 bg-gray-800 p-4 text-white">
    <h2 className="mb-2 text-xl font-bold text-yellow-400">Add your licensed vehicle</h2>
    <p className="mb-4 text-sm">
      You already have an ACT driver application. Submit a vehicle and its evidence here.
      Do not create another driver account.
    </p>
    {done ? <p role="status" className="rounded bg-green-900/40 p-3">{message}</p> : (
      <form onSubmit={submit} className="space-y-4">
        <label className="block text-sm font-medium">Vehicle ownership *
          <select value={ownership} className={baseInput} onChange={e => setOwnership(e.target.value)}>
            <option value="phv_owner">I own a licensed PHV</option>
            <option value="hiring_a_phv">I hire a licensed PHV</option>
            <option value="other">Other lawful arrangement</option>
          </select>
        </label>
        <label className="block text-sm font-medium">ACT vehicle class *
          <select required value={fields.vehicle_class_code} className={baseInput}
            onChange={e => set("vehicle_class_code", e.target.value)}>
            <option value="">Select...</option>
            {classes.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
          </select>
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          {field("vehicle_make", "Make")}
          {field("vehicle_model", "Model")}
          {field("vehicle_year", "Year (2015 or newer)", "number")}
          {field("vehicle_registration", "Vehicle registration")}
          {field("vehicle_colour", "Colour")}
          {field("mot_expiry", "MOT expiry", "date")}
          {field("insurance_expiry", "Insurance expiry", "date")}
        </div>
        <label className="block text-sm font-medium">Accepts pets? *
          <select required className={baseInput} value={fields.accepts_pets}
            onChange={e => set("accepts_pets", e.target.value)}>
            <option value="">Select...</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </label>
        {ownership === "other" && field("ownership_explanation", "Describe your lawful right to use the vehicle")}
        {upload("mot", "MOT certificate", true)}
        {upload("insurance", "Insurance certificate", true)}
        {upload("vehicle_phv", "TfL vehicle PHV licence", true)}
        {(ownership === "phv_owner" || ownership === "other") &&
          upload("v5c", "V5C logbook", ownership === "phv_owner")}
        {(ownership === "hiring_a_phv" || ownership === "other") &&
          upload("hire_agreement", "Vehicle hire/right-to-use agreement", ownership === "hiring_a_phv")}
        {message && <p role="alert" className="rounded bg-red-900/50 p-3">{message}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-yellow-400 p-3 font-bold text-black disabled:opacity-40">
          {busy ? "Submitting evidence..." : "Submit vehicle for ACT verification"}
        </button>
      </form>
    )}
  </section>;
}
