"use client";

import React, { useState } from "react";
import { patchData } from "@/lib/api/patchApi";
import { extract_error } from "@/lib/api/errorApi";
import { toast } from "react-toastify";

type DriverRecord = {
  id: number;
  driver?: {
    pco_licence_number?: string | null;
    driver_photo?: string | null;
    user?: { first_name?: string; last_name?: string };
  };
  vehicle?: {
    make?: string | null;
    model?: string | null;
    color?: string | null;
    vehicle_number?: string | null;
  };
};

type Props = {
  driver: DriverRecord;
  token?: string;
  onClose: () => void;
  onSaved: (updated: DriverRecord) => void;
};

/**
 * Reuses the existing authenticated admin driver update endpoint.
 * Identity evidence stays on ACT; neither licence details nor photo contents
 * are sent through chat, stored in localStorage, or exposed in a URL.
 */
export default function DriverPassengerDetailsEditor({
  driver,
  token,
  onClose,
  onSaved,
}: Props) {
  const [licenceNumber, setLicenceNumber] = useState(
    driver.driver?.pco_licence_number ?? "",
  );
  const [make, setMake] = useState(driver.vehicle?.make ?? "");
  const [model, setModel] = useState(driver.vehicle?.model ?? "");
  const [colour, setColour] = useState(driver.vehicle?.color ?? "");
  const [photo, setPhoto] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const existingPhoto = Boolean(driver.driver?.driver_photo);

  const save = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (saving) return;
    setError("");

    if (!token) {
      setError("Admin session expired. Please sign in again.");
      return;
    }
    if (!licenceNumber.trim() || !make.trim() || !model.trim() || !colour.trim()) {
      setError("Enter the verified driver licence number and vehicle make, model and colour.");
      return;
    }
    if (!existingPhoto && !photo) {
      setError("Upload a genuine driver photograph.");
      return;
    }
    if (photo && (!["image/jpeg", "image/png"].includes(photo.type) || photo.size > 5 * 1024 * 1024)) {
      setError("Driver photograph must be a JPEG or PNG image no larger than 5 MB.");
      return;
    }

    const data = new FormData();
    data.append("pco_licence_number", licenceNumber.trim());
    data.append("vehicle_make", make.trim());
    data.append("vehicle_model", model.trim());
    data.append("vehicle_color", colour.trim());
    if (photo) data.append("driver_photo", photo);

    setSaving(true);
    try {
      const response = await patchData<{ success: boolean; data: DriverRecord }>({
        endpoint: `/api/admin-panel/drivers/${driver.id}/update/`,
        body: data,
        token,
        isFormData: true,
      });
      if (!response.success) {
        throw new Error("The driver profile was not saved.");
      }
      toast.success("Driver passenger details saved.");
      onSaved(response.data);
    } catch (err: any) {
      setError(extract_error(err) || err?.message || "Unable to save driver details.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 p-3">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Edit driver passenger-facing details"
        className="w-full max-w-xl overflow-y-auto rounded-xl border border-border bg-card p-5 shadow-xl max-h-[92vh]"
      >
        <div className="mb-4">
          <h2 className="text-lg font-bold text-foreground">Edit driver passenger-facing details</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter the driver's actual TfL details. These are required before an ACT driver can accept a booking.
            The vehicle registration and class will not change.
          </p>
          <p className="mt-2 text-sm font-medium text-foreground">
            {driver.driver?.user?.first_name} {driver.driver?.user?.last_name}
            {" — "}{driver.vehicle?.vehicle_number || "Vehicle not specified"}
          </p>
        </div>
        <form onSubmit={save} className="space-y-4">
          <label className="block text-sm font-semibold text-foreground">
            TfL PHV driver licence number
            <input
              required
              maxLength={50}
              autoComplete="off"
              value={licenceNumber}
              onChange={(e) => setLicenceNumber(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background p-3 text-foreground"
            />
          </label>
          <label className="block text-sm font-semibold text-foreground">
            Vehicle make
            <input
              required
              maxLength={80}
              autoComplete="off"
              value={make}
              onChange={(e) => setMake(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background p-3 text-foreground"
            />
          </label>
          <label className="block text-sm font-semibold text-foreground">
            Vehicle model
            <input
              required
              maxLength={80}
              autoComplete="off"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background p-3 text-foreground"
            />
          </label>
          <label className="block text-sm font-semibold text-foreground">
            Vehicle colour
            <input
              required
              maxLength={50}
              autoComplete="off"
              value={colour}
              onChange={(e) => setColour(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background p-3 text-foreground"
            />
          </label>
          <label className="block text-sm font-semibold text-foreground">
            Driver photograph {existingPhoto ? "(on file; replace only if needed)" : "(required)"}
            <input
              type="file"
              accept="image/png,image/jpeg"
              onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
              className="mt-2 block w-full text-sm text-foreground"
            />
          </label>
          {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              disabled={saving}
              onClick={onClose}
              className="flex-1 rounded-md border border-border bg-background px-3 py-3 font-semibold text-foreground disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 rounded-md bg-yellow-500 px-3 py-3 font-semibold text-black disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save driver details"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
