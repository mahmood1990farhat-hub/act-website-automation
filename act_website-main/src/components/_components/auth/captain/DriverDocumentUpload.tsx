"use client";

import { useId, useRef } from "react";

export const DOCUMENT_LIMIT_BYTES = 10 * 1024 * 1024;

/** Browser guidance only; the existing backend still verifies real content. */
export function documentError(file: File, imageOnly = false): string {
  if (file.size === 0) return "This file is empty. Choose another file.";
  if (file.size > DOCUMENT_LIMIT_BYTES) return "Choose a file no larger than 10 MB.";
  const allowed = imageOnly ? ["image/jpeg", "image/png"] : ["application/pdf", "image/jpeg", "image/png"];
  if (!allowed.includes(file.type)) {
    return imageOnly ? "Choose a JPG or PNG photograph." : "Choose a PDF, JPG or PNG document.";
  }
  return "";
}

type Props = {
  name: string;
  label: string;
  required?: boolean;
  file?: File;
  imageOnly?: boolean;
  disabled?: boolean;
  onChange: (file: File | undefined) => void;
};

/** The parent's File is the single source for display, validation and submission.
 * The native picker is deliberately not used as a second, conflicting status.
 */
export default function DriverDocumentUpload({ name, label, required = true, file,
  imageOnly = false, disabled = false, onChange }: Props) {
  const id = useId();
  const picker = useRef<HTMLInputElement>(null);
  const action = useRef<HTMLButtonElement>(null);
  const issue = file ? documentError(file, imageOnly) : "";
  return (
    <div data-document={name} role="group" aria-labelledby={`${id}-label`}
      className="min-w-0 space-y-3 rounded-xl border border-gray-600 bg-gray-800/50 p-4">
      <p id={`${id}-label`} className="text-sm font-semibold leading-6 text-white">
        {label} {required ? <span aria-label="required">*</span> : <span className="font-normal text-gray-300">(optional at application)</span>}
      </p>
      <p id={`${id}-hint`} className="text-xs leading-5 text-gray-300">
        {imageOnly ? "JPG or PNG" : "PDF, JPG or PNG"} · Maximum 10 MB per file
      </p>
      <input ref={picker} type="file" hidden tabIndex={-1} name={name}
        aria-label={`Choose file for ${label}`} disabled={disabled}
        accept={imageOnly ? ".jpg,.jpeg,.png,image/jpeg,image/png" : ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"}
        onChange={event => {
          const chosen = event.currentTarget.files?.[0];
          // An empty picker result/cancellation must not remove the saved File.
          // Reset only the picker so choosing the same file again fires change.
          event.currentTarget.value = "";
          if (chosen) onChange(chosen);
        }} />
      <div className="flex flex-wrap items-center gap-3">
        <button ref={action} type="button" disabled={disabled}
          aria-labelledby={`${id}-action ${id}-label`}
          aria-describedby={`${id}-hint ${id}-status${issue ? ` ${id}-error` : ""}`}
          aria-invalid={!!issue}
          onClick={() => picker.current?.click()}
          className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-yellow-400 px-4 py-3 text-sm font-bold text-black hover:bg-yellow-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-yellow-400 disabled:opacity-50 sm:w-auto">
          <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4" />
          </svg>
          <span id={`${id}-action`}>{file ? "Replace document" : "Upload your document"}</span>
        </button>
        {file && <button type="button" disabled={disabled} aria-label={`Remove ${label}`}
          className="min-h-12 rounded-lg border border-gray-400 px-4 py-3 text-sm text-white hover:bg-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-yellow-400 disabled:opacity-50"
          onClick={() => {
            onChange(undefined);
            if (picker.current) picker.current.value = "";
            action.current?.focus();
          }}>Remove</button>}
      </div>
      <div id={`${id}-status`} aria-live="polite" aria-atomic="true" className="min-w-0 text-sm">
        {file ? <>
          <p className="break-all font-semibold text-yellow-300" data-selected-filename>{file.name}</p>
          <p className="mt-1 text-xs text-gray-300">{issue ? "Not ready — choose a valid file." : "Selected — ready to submit. Not uploaded yet."}</p>
        </> : <p className="text-gray-300">No document selected.</p>}
      </div>
      {issue && <p id={`${id}-error`} role="alert" className="text-sm text-red-200">{issue}</p>}
    </div>
  );
}
