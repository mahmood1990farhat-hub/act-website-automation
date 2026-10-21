"use client";

import { useEffect, useRef, useState } from "react";
import type { Locale } from "../../../../../i18n.config";
import DriverDocumentUpload, { documentError } from "./DriverDocumentUpload";
import DriverVehicleFields, { VEHICLE_OWNERSHIP_LABELS } from "./DriverVehicleFields";

type Draft = {
  first_name: string; last_name: string; date_of_birth: string;
  phone_number: string; email: string; address: string; postcode: string;
  pco_badge_number: string; pco_badge_expiry: string; years_experience: string;
  vehicle_ownership: string; vehicle_class_code: string; vehicle_make: string;
  vehicle_model: string; vehicle_year: string; vehicle_registration: string;
  vehicle_colour: string; mot_expiry: string; insurance_expiry: string;
  accepts_pets: string; ownership_explanation: string;
  agrees_policies: boolean; dbs_consent: boolean;
  passenger_photo_disclosure_consent: boolean;
};
const initial: Draft = {
  first_name: "", last_name: "", date_of_birth: "", phone_number: "+44",
  email: "", address: "", postcode: "", pco_badge_number: "",
  pco_badge_expiry: "", years_experience: "", vehicle_ownership: "",
  vehicle_class_code: "", vehicle_make: "", vehicle_model: "",
  vehicle_year: "", vehicle_registration: "", vehicle_colour: "",
  mot_expiry: "", insurance_expiry: "", accepts_pets: "",
  ownership_explanation: "", agrees_policies: false, dbs_consent: false,
  passenger_photo_disclosure_consent: false,
};
type DocKind = "pco_front" | "pco_back" | "dvla_front" | "dvla_back" |
  "driver_photo" | "mot" | "insurance" | "v5c" | "vehicle_phv" |
  "hire_agreement" | "dbs";
const identityDocs: { name: DocKind; label: string }[] = [
  { name: "pco_front", label: "TfL PHV badge — front" },
  { name: "pco_back", label: "TfL PHV badge — back" },
  { name: "dvla_front", label: "DVLA driving licence — front" },
  { name: "dvla_back", label: "DVLA driving licence — back" },
  { name: "driver_photo", label: "Driver photograph (for passenger disclosure after approval)" },
];
const vehicleDocs: { name: DocKind; label: string }[] = [
  { name: "mot", label: "MOT certificate" },
  { name: "insurance", label: "Valid vehicle insurance" },
  { name: "vehicle_phv", label: "Vehicle PHV licence" },
];
const steps = ["Personal details", "TfL / Driver", "Vehicle & evidence", "Review & submit"];
const fieldClass = "mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-3 text-gray-900 focus:border-yellow-500 focus:outline-none";
const labelClass = "block text-sm font-semibold text-white";

export default function UnifiedDriverApplication({ locale }: { locale: Locale }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<Draft>(initial);
  const [files, setFiles] = useState<Partial<Record<DocKind, File>>>({});
  const [options, setOptions] = useState<{ description: string; place_id: string }[]>([]);
  const [serverError, setServerError] = useState("");
  const [validationStep, setValidationStep] = useState<number | null>(null);
  const submitting = useRef(false);
  const [pending, setPending] = useState(false);
  const [success, setSuccess] = useState<{ application_id: number; status: string } | null>(null);
  const hasVehicle = form.vehicle_ownership !== "do_not_have_a_phv";
  const put = (name: keyof Draft, value: string | boolean) => {
    setServerError("");
    setForm(previous => ({ ...previous, [name]: value }));
  };
  const includesDocument = (name: DocKind) =>
    identityDocs.some(doc => doc.name === name) || name === "dbs" || (hasVehicle && (
      vehicleDocs.some(doc => doc.name === name) ||
      (name === "v5c" && ["phv_owner", "other"].includes(form.vehicle_ownership)) ||
      (name === "hire_agreement" && ["hiring_a_phv", "other"].includes(form.vehicle_ownership))
    ));

  // Reuse ACT's existing Google Places proxy; the free-text input remains
  // editable when Places is offline, so applicants are not locked out.
  useEffect(() => {
    if (step !== 1 || form.address.trim().length < 3) {
      setOptions([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const url = "/api/places?input=" + encodeURIComponent(form.address) +
          "&language=en&components=country:gb";
        const result = await fetch(url, { signal: controller.signal });
        const data = await result.json();
        setOptions(data.status === "OK" && Array.isArray(data.predictions)
          ? data.predictions.slice(0, 5).map((row: any) => ({
            description: String(row.description || ""),
            place_id: String(row.place_id || ""),
          })) : []);
      } catch {
        if (!controller.signal.aborted) setOptions([]);
      }
    }, 450);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [step, form.address]);

  const checkStep = (which: number): string => {
    if (which === 1) {
      if (!form.first_name.trim() || !form.last_name.trim() ||
          !form.date_of_birth || !form.address.trim() ||
          !form.postcode.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) {
        return "Complete your name, date of birth, email and UK address/postcode.";
      }
      if (!/^\+447\d{9}$/.test(form.phone_number.replace(/[\s()-]/g, ""))) {
        return "Enter a UK mobile number in +447XXXXXXXXX format.";
      }
      const dob = new Date(form.date_of_birth + "T12:00:00");
      const limit = new Date(); limit.setFullYear(limit.getFullYear() - 21);
      if (Number.isNaN(dob.getTime()) || dob > limit) return "Applicants must be at least 21 years old.";
    }
    if (which === 2) {
      if (!form.pco_badge_number.trim() || !form.pco_badge_expiry ||
          form.pco_badge_expiry <= new Date().toISOString().slice(0, 10) ||
          !form.years_experience) return "Provide your real TfL badge number, valid expiry and experience.";
      for (const { name, label } of identityDocs) if (!files[name]) return "Select your " + label + ".";
    }
    if (which === 3) {
      if (!form.vehicle_ownership) return "Select your vehicle ownership status.";
      if (hasVehicle) {
        const required: (keyof Draft)[] = [
          "vehicle_class_code", "vehicle_make", "vehicle_model", "vehicle_year",
          "vehicle_registration", "vehicle_colour", "mot_expiry",
          "insurance_expiry", "accepts_pets",
        ];
        if (required.some(name => !String(form[name]).trim())) return "Complete all vehicle, expiry, class and pet fields.";
        if (!Number.isInteger(Number(form.vehicle_year)) || Number(form.vehicle_year) < 2015 ||
            Number(form.vehicle_year) > new Date().getFullYear())
          return "Enter a valid vehicle year (2015–present).";
        if (form.mot_expiry <= new Date().toISOString().slice(0, 10) ||
            form.insurance_expiry <= new Date().toISOString().slice(0, 10))
          return "MOT and insurance expiry dates must be in the future.";
        for (const { name, label } of vehicleDocs) if (!files[name]) return "Select your " + label + ".";
        if (form.vehicle_ownership === "phv_owner" && !files.v5c)
          return "Vehicle owners must upload the V5C logbook.";
        if (form.vehicle_ownership === "hiring_a_phv" && !files.hire_agreement)
          return "Select your rental / hire / lease agreement.";
        if (form.vehicle_ownership === "other" &&
            (!form.ownership_explanation.trim() || (!files.v5c && !files.hire_agreement)))
          return "Explain the ownership arrangement and upload proof of lawful use.";
      }
    }
    if (which === 4 && (!form.agrees_policies || !form.dbs_consent ||
        !form.passenger_photo_disclosure_consent)) {
      return "You must agree to the ACT policies and DBS verification requirement.";
    }
    // Validate only the documents belonging to this step and ownership path.
    // Stored File objects, not a remounted native input, are authoritative.
    const documents = which === 2 ? [...identityDocs, { name: "dbs" as DocKind, label: "DBS certificate" }]
      : which === 3 ? [...vehicleDocs, { name: "v5c" as DocKind, label: "V5C logbook" },
        { name: "hire_agreement" as DocKind, label: "Rental / hire / lease agreement" }] : [];
    for (const { name, label } of documents) {
      const file = files[name];
      if (file && includesDocument(name)) {
        const issue = documentError(file, name === "driver_photo");
        if (issue) return label + ": " + issue;
      }
    }
    return "";
  };
  // Recompute a shown client error when its fields/files change; never keep a
  // stale missing-document or consent warning after the relevant fix.
  const error = serverError || (validationStep !== null ? checkStep(validationStep) : "");
  const next = () => {
    setServerError("");
    setValidationStep(step);
    if (checkStep(step)) return;
    setValidationStep(null); setStep(current => Math.min(4, current + 1));
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting.current) return;
    if (step !== 4) { next(); return; }
    // Only deliberate activation of the final button can POST the application.
    const submitter = (event.nativeEvent as SubmitEvent).submitter;
    if (submitter?.getAttribute("data-act-submit") !== "true") return;
    for (let section = 1; section <= 4; section++) {
      const issue = checkStep(section);
      if (issue) { setStep(section); setServerError(""); setValidationStep(section); return; }
    }
    submitting.current = true;
    setPending(true); setServerError(""); setValidationStep(null);
    try {
      const body = new FormData();
      for (const [key, value] of Object.entries(form)) {
        if (!hasVehicle && [
          "vehicle_class_code", "vehicle_make", "vehicle_model", "vehicle_year",
          "vehicle_registration", "vehicle_colour", "mot_expiry",
          "insurance_expiry", "accepts_pets", "ownership_explanation",
        ].includes(key)) continue;
        if (value !== "") body.append(key, String(value));
      }
      for (const [key, file] of Object.entries(files)) {
        if (file && includesDocument(key as DocKind))
          body.append(key, file);
      }
      const response = await fetch(
        (process.env.NEXT_PUBLIC_API_BASE_URL || "") + "/api/drivers/onboarding/apply/",
        { method: "POST", body },
      );
      const payload = await response.json();
      if (!response.ok) {
        const detail = payload?.detail || payload?.message ||
          Object.entries(payload).map(([key, value]) => key + ": " + String(value)).join("; ");
        throw new Error(String(detail || "Unable to submit application."));
      }
      setSuccess({ application_id: payload.application_id, status: payload.status });
    } catch (caught: any) {
      setServerError(caught?.message || "Application could not be submitted.");
    } finally {
      submitting.current = false;
      setPending(false);
    }
  };

  const input = (name: keyof Draft, label: string, type = "text", optionsList?: { value: string; label: string }[]) => (
    <label className={labelClass} key={name}>
      {label} *
      {optionsList ? (
        <select className={fieldClass} required value={String(form[name])}
          onChange={event => put(name, event.target.value)}>
          <option value="">Select...</option>
          {optionsList.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}
        </select>
      ) : (
        <input className={fieldClass} type={type} required
          value={String(form[name])} onChange={event => put(name, event.target.value)}
          autoComplete={name === "email" ? "email" : name === "phone_number" ? "tel" : "off"}
        />
      )}
    </label>
  );
  const fileInput = (name: DocKind, label: string, required = true) => (
    <DriverDocumentUpload key={name} name={name} label={label} required={required}
      file={files[name]} imageOnly={name === "driver_photo"} disabled={pending}
      onChange={file => {
        setServerError("");
        setFiles(old => {
          const updated = { ...old };
          if (file) updated[name] = file; else delete updated[name];
          return updated;
        });
      }} />
  );

  if (success) return (
    <section className="mx-auto max-w-2xl rounded-xl border border-green-400 bg-gray-900 p-6 text-white">
      <h2 className="text-2xl font-bold text-yellow-400">Application received</h2>
      <p className="my-3">Reference #{success.application_id} — {success.status.replace(/_/g, " ")}.</p>
      <p>Check your email for a secure password setup link. Your application remains subject to ACT's document and driver eligibility review. Do not submit again.</p>
      <a className="mt-4 inline-block underline text-yellow-400" href={`/${locale}/auth`}>Driver login</a>
    </section>
  );

  return (
    <form onSubmit={submit} noValidate aria-label="ACT driver application"
      style={{ paddingBottom: "max(2rem, env(safe-area-inset-bottom))" }}
      className="mx-auto w-full min-w-0 max-w-3xl space-y-5 rounded-2xl border border-gray-700 bg-gray-900 p-4 text-white sm:p-8">
      <h1 className="text-2xl font-bold text-yellow-400">Apply to drive with ACT</h1>
      <p className="text-sm text-gray-200">One application. Secure documents. ACT verifies every driver before allocating work.</p>
      <ol className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        {steps.map((title, index) =>
          <li key={title} className={`rounded-lg p-2 ${index + 1 === step ? "bg-yellow-400 text-black font-bold" : "bg-gray-800 text-gray-200"}`}>
            {index + 1}. {title}
          </li>,
        )}
      </ol>
      {step === 1 && <div className="grid gap-4 sm:grid-cols-2">
        {input("first_name", "First name")}
        {input("last_name", "Last name")}
        {input("date_of_birth", "Date of birth (21+)", "date")}
        {input("phone_number", "UK mobile (+44)", "tel")}
        {input("email", "Email", "email")}
        {input("postcode", "Postcode")}
        <div className="relative sm:col-span-2">
          {input("address", "Current UK address")}
          {options.length > 0 && <ul className="absolute z-20 mt-1 max-h-48 w-full overflow-y-auto rounded bg-white text-black shadow-lg">
            {options.map(opt => <li key={opt.place_id}>
              <button type="button" className="w-full p-3 text-left hover:bg-yellow-100"
                onClick={() => { put("address", opt.description); setOptions([]); }}>
                {opt.description}
              </button>
            </li>)}
          </ul>}
          <p className="mt-1 text-xs text-gray-300">Select a Google Places result or enter your address manually.</p>
        </div>
      </div>}
      {step === 2 && <div className="space-y-4">
        {input("pco_badge_number", "TfL PHV driver badge number")}
        {input("pco_badge_expiry", "TfL badge expiry", "date")}
        {input("years_experience", "Years of driving experience", "text", [
          { value: "less_than_1", label: "Less than 1 year" },
          { value: "1_to_3", label: "1–3 years" },
          { value: "3_to_5", label: "3–5 years" },
          { value: "5_plus", label: "5+ years" },
        ])}
        <div className="grid gap-4 sm:grid-cols-2">
          {identityDocs.map(d => fileInput(d.name, d.label))}
          {fileInput("dbs", "DBS certificate", false)}
        </div>
        <div className="rounded-lg border border-yellow-400/40 bg-gray-800 p-4 text-sm leading-6 text-gray-200">
          <strong className="block text-yellow-300">DBS evidence is needed before final approval</strong>
          You can submit this application without a DBS certificate. If ACT accepts your application in principle
          and you have not provided it, ACT will request it through the secure application portal.
          You cannot receive trips until ACT has completed the required DBS, driver and vehicle checks.
        </div>
      </div>}
      {step === 3 && <div className="space-y-4">
        {input("vehicle_ownership", "Vehicle ownership", "text", [
          { value: "phv_owner", label: "I own a licensed PHV" },
          { value: "hiring_a_phv", label: VEHICLE_OWNERSHIP_LABELS.hiring_a_phv },
          { value: "do_not_have_a_phv", label: "I do not have a vehicle yet" },
          { value: "other", label: "Other lawful arrangement" },
        ])}
        {!hasVehicle ? <p className="rounded-lg bg-yellow-500/15 p-4 text-yellow-100">
          You can apply without a vehicle. You cannot receive bookings until ACT has verified a suitable licensed vehicle and documents.
        </p> : <div className="grid gap-4 sm:grid-cols-2">
          <DriverVehicleFields value={form} fieldClass={fieldClass} labelClass={labelClass}
            onChange={patch => { setServerError(""); setForm(previous => ({ ...previous, ...patch })); }} />
          {input("vehicle_class_code", "ACT vehicle class", "text", [
            { value: "comfort", label: "Comfort Class (5 seater)" },
            { value: "comfort_xl", label: "Comfort XL (MPV)" },
            { value: "executive", label: "Executive Class" },
            { value: "executive_xl", label: "Executive XL (van)" },
            { value: "first_class", label: "First Class" },
          ])}
          {input("vehicle_registration", "Vehicle registration (VRM)")}
          {input("vehicle_colour", "Vehicle colour")}
          {input("mot_expiry", "MOT expiry", "date")}
          {input("insurance_expiry", "Insurance expiry", "date")}
          {input("accepts_pets", "Accepts pets?", "text", [
            { value: "true", label: "Yes" },
            { value: "false", label: "No" },
          ])}
          {form.vehicle_ownership === "other" && input("ownership_explanation", "Explain your lawful right to use this vehicle")}
          <div className="space-y-4 sm:col-span-2">
            {vehicleDocs.map(d => fileInput(d.name, d.label))}
            {(form.vehicle_ownership === "phv_owner" || form.vehicle_ownership === "other") &&
              fileInput("v5c", "V5C logbook", form.vehicle_ownership === "phv_owner")}
            {(form.vehicle_ownership === "hiring_a_phv" || form.vehicle_ownership === "other") &&
              fileInput("hire_agreement", "Rental / hire / lease agreement", form.vehicle_ownership === "hiring_a_phv")}
          </div>
        </div>}
      </div>}
      {step === 4 && <div className="space-y-4 text-sm">
        <p>Review your application before submitting. A password is not required now.</p>
        <div className="space-y-2 break-words rounded-lg bg-gray-800 p-4">
          <p><strong>Applicant:</strong> {form.first_name} {form.last_name}</p>
          <p><strong>Email:</strong> {form.email}</p>
          <p><strong>Phone:</strong> {form.phone_number}</p>
          <p><strong>Date of birth:</strong> {form.date_of_birth}</p>
          <p><strong>Address:</strong> {form.address}, {form.postcode}</p>
          <p><strong>TfL badge:</strong> {form.pco_badge_number} · Expires {form.pco_badge_expiry}</p>
          <p><strong>Vehicle arrangement:</strong> {VEHICLE_OWNERSHIP_LABELS[form.vehicle_ownership] || "Not selected"}</p>
          {hasVehicle && <>
            <p><strong>Vehicle:</strong> {form.vehicle_make} {form.vehicle_model} — {form.vehicle_registration}</p>
            <p><strong>Year / colour:</strong> {form.vehicle_year} / {form.vehicle_colour}</p>
            <p><strong>Expiry dates:</strong> MOT {form.mot_expiry}; insurance {form.insurance_expiry}</p>
          </>}
          <p className="pt-2 font-semibold">Selected documents — sent only when you submit:</p>
          <ul className="list-inside list-disc space-y-1">
            {[...identityDocs, ...vehicleDocs, { name: "v5c" as DocKind, label: "V5C logbook" },
              { name: "hire_agreement" as DocKind, label: "Rental / hire / lease agreement" },
              { name: "dbs" as DocKind, label: "DBS certificate" }]
              .filter(doc => includesDocument(doc.name) && files[doc.name])
              .map(doc => <li key={doc.name}>{doc.label}: <span className="break-all">{files[doc.name]!.name}</span></li>)}
          </ul>
          <div className="flex flex-wrap gap-2 pt-3">
            {[1, 2, 3].map(section => <button type="button" key={section}
              className="min-h-12 rounded-lg border border-gray-500 px-3 py-2 text-yellow-300"
              onClick={() => { setStep(section); setValidationStep(null); setServerError(""); }}>
              Edit {steps[section - 1]}
            </button>)}
          </div>
        </div>
        <label className="flex min-h-12 items-start gap-3 py-2">
          <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-yellow-400" checked={form.agrees_policies}
            onChange={event => put("agrees_policies", event.target.checked)} />
          <span>I confirm the information is genuine and agree to ACT's{" "}
          <a href={`/documents/${locale}/terms-and-conditions.pdf`} target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline">driver terms</a>
          {" "}and{" "}
          <a href={`/documents/${locale}/privacy-policy.pdf`} target="_blank" rel="noopener noreferrer" className="text-yellow-400 underline">privacy policy</a>.</span>
        </label>
        <label className="flex min-h-12 items-start gap-3 py-2">
          <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-yellow-400" checked={form.dbs_consent}
            onChange={event => put("dbs_consent", event.target.checked)} />
          I understand ACT must check my DBS status and all necessary licences before allowing trips.
        </label>
        <label className="flex min-h-12 items-start gap-3 py-2">
          <input type="checkbox" className="mt-1 h-5 w-5 shrink-0 accent-yellow-400" checked={form.passenger_photo_disclosure_consent}
            onChange={event => put("passenger_photo_disclosure_consent", event.target.checked)} />
          I understand my verified first name, PHV driver licence number, photograph and vehicle details will be shared with passengers when I am assigned a journey.
        </label>
        <p className="text-xs text-gray-300">Your original identity documents are stored privately and reviewed only by authorized ACT staff.</p>
      </div>}
      {error && <p role="alert" className="rounded-lg border border-red-500 bg-red-900/30 p-3 text-sm text-red-200">{error}</p>}
      <div className="flex flex-wrap gap-3 border-t border-gray-700 pb-6 pt-4">
        {step > 1 && <button type="button" disabled={pending}
          className="min-h-12 rounded-lg border border-gray-500 px-5 py-3" onClick={() => { setStep(step - 1); setValidationStep(null); setServerError(""); }}>
          Back
        </button>}
        {step < 4 ? <button key="continue" type="button" onClick={next} className="ml-auto min-h-12 rounded-lg bg-yellow-400 px-6 py-3 font-bold text-black">
          Continue
        </button> : <button key="submit" data-act-submit="true" type="submit" disabled={pending}
          className="ml-auto min-h-12 rounded-lg bg-yellow-400 px-6 py-3 font-bold text-black disabled:opacity-50">
          {pending ? "Submitting securely..." : "Submit application"}
        </button>}
      </div>
    </form>
  );
}
