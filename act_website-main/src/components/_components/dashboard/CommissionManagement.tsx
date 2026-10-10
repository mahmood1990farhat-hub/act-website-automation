"use client";

import { useEffect, useRef, useState } from "react";
import { commissionCsv, commissionLists, validCommissionPercentage, type CommissionSnapshot } from "@/lib/commission-management";

const endpoint = "/api/admin-panel/commission-management/";
const inputClass = "w-full rounded-lg border border-gray-300 bg-white p-3 text-gray-900 disabled:bg-gray-100";
const buttonClass = "rounded-lg bg-[#ffd100] px-4 py-2 font-semibold text-gray-900 disabled:cursor-not-allowed disabled:opacity-40";

export default function CommissionManagement({ token, locale }: { token?: string; locale: string }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<CommissionSnapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reason, setReason] = useState("");
  const [globalRate, setGlobalRate] = useState("");
  const [driverId, setDriverId] = useState("");
  const [individualRate, setIndividualRate] = useState("");
  const [editingException, setEditingException] = useState(false);
  const [groupId, setGroupId] = useState("");
  const [groupName, setGroupName] = useState("");
  const [groupRate, setGroupRate] = useState("");
  const [memberIds, setMemberIds] = useState<string[]>([]);

  async function request(body?: Record<string, unknown>): Promise<CommissionSnapshot> {
    if (!token) throw new Error("Sign in to ACT Admin to view commissions.");
    const base = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!base) throw new Error("The admin API connection is not configured.");
    const response = await fetch(`${base}${endpoint}`, {
      method: body ? "POST" : "GET", cache: "no-store",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (response.status === 401) {
      window.location.assign(`/${locale}/admin/login`);
      throw new Error("Your admin session expired. Please sign in again.");
    }
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail ?? payload.message ?? payload;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const result = payload.data as CommissionSnapshot;
    commissionLists(result); // Refuse duplicate driver rows before presenting controls.
    return result;
  }

  async function refresh() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError("");
    try {
      const result = await request();
      setData(result); setGlobalRate(result.global_percentage);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load commission settings.");
      setData(null);
    } finally { inFlight.current = false; setBusy(false); }
  }

  useEffect(() => {
    if (open) void refresh();
    // Only load when opened or the authenticated admin context changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, token, locale]);

  async function save(action: string, fields: Record<string, unknown>) {
    if (!data || !data.writes_enabled || inFlight.current) return;
    if (!reason.trim()) { setError("Enter a reason for this change."); return; }
    if (typeof fields.company_percentage === "string" && !validCommissionPercentage(fields.company_percentage)) {
      setError("Enter an ACT deduction between 0 and 100, with at most two decimal places."); return;
    }
    if (!window.confirm("Save this commission configuration? Passenger charges and existing ledger entries will not be edited.")) return;
    inFlight.current = true; setBusy(true); setError(""); setMessage("");
    try {
      const result = await request({ action, ...fields, reason: reason.trim(), revision: data.revision });
      setData(result); setGlobalRate(result.global_percentage);
      setDriverId(""); setIndividualRate(""); setEditingException(false);
      setGroupId(""); setGroupName(""); setGroupRate(""); setMemberIds([]); setReason("");
      setMessage("Saved. The lists now show the recorded commission categories.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Changes were not saved. Refresh before trying again.");
    } finally { inFlight.current = false; setBusy(false); }
  }

  function exportCsv() {
    if (!data) return;
    const url = URL.createObjectURL(new Blob([commissionCsv(data)], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "act-driver-commissions.csv";
    document.body.appendChild(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const lists = data ? commissionLists(data) : null;
  const locked = busy || !data?.writes_enabled || Boolean(data?.multiple_global_rules || lists?.conflicts.length);
  const selectedGroup = data?.groups.find((group) => group.id === Number(groupId));
  const ownMembers = lists?.grouped.filter((driver) => driver.group_id === selectedGroup?.id) ?? [];
  const availableExceptions = editingException ? lists?.individual ?? [] : lists?.global ?? [];

  return (
    <section className="mb-6 rounded-xl border border-gray-200 bg-white text-gray-900 shadow-sm" dir="ltr">
      <button type="button" aria-expanded={open} aria-controls="act-commission-controls"
        onClick={() => setOpen(!open)} className="flex w-full items-center justify-between p-5 text-left text-xl font-bold">
        <span>Driver Finance · Commission Management</span><span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>
      {open && <div id="act-commission-controls" className="space-y-6 border-t p-4 sm:p-6">
        <p className="text-sm text-gray-600">ACT deduction is the percentage retained by ACT, not the driver’s share. Each driver belongs to one commission category.</p>
        <div className="flex flex-wrap gap-3">
          <button type="button" className={buttonClass} disabled={busy} onClick={() => void refresh()}>Refresh lists</button>
          <button type="button" className={buttonClass} disabled={!data || busy} onClick={exportCsv}>Export CSV for Excel</button>
        </div>
        {busy && <p role="status">Loading or saving commission settings…</p>}
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-red-800">{error}</p>}
        {message && <p role="status" className="rounded-lg bg-green-50 p-3 text-green-800">{message}</p>}
        {data && lists && <>
          {!data.writes_enabled && <p role="status" className="rounded-lg bg-amber-50 p-3 text-amber-900">{data.write_lock_reason}</p>}
          {data.legacy_vehicle_rules.length > 0 && <p className="rounded-lg bg-amber-50 p-3">Existing vehicle-specific commission rules override the global rate. Global saving remains blocked until their transition is reviewed. Groups and individual rates are listed separately.</p>}
          {(data.multiple_global_rules || lists.conflicts.length > 0) && <p role="alert">Conflicting legacy commission records require review. Saving is disabled; no records have been changed.</p>}
          <label className="block text-sm font-medium">Reason for the next change
            <input className={inputClass} value={reason} maxLength={500} disabled={locked}
              onChange={(event) => setReason(event.target.value)} placeholder="Record why this rate or membership is changing" />
          </label>

          <section className="space-y-4 rounded-xl border p-4" aria-labelledby="global-commission-title">
            <h3 id="global-commission-title" className="text-lg font-bold">ACT Global Commissions</h3>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium">Drivers
                <select className={inputClass} value="all" onChange={() => undefined}>
                  <option value="all">All global drivers ({lists.global.length})</option>
                  {lists.global.map((driver) => <option key={driver.id} disabled value={driver.id}>{driver.name} (#{driver.id})</option>)}
                </select>
              </label>
              <label className="text-sm font-medium">ACT commission deducted (%)
                <input className={inputClass} type="number" min="0" max="100" step="0.01" inputMode="decimal"
                  value={globalRate} disabled={locked} onChange={(event) => setGlobalRate(event.target.value)} />
              </label>
            </div>
            <p className="text-sm text-gray-600">Individual exceptions and group members are excluded automatically. New drivers without a separate assignment inherit the default.</p>
            {!data.global_is_configured && <p className="text-sm">The displayed rate is the existing fallback, not a newly approved rate.</p>}
            <button type="button" className={buttonClass} disabled={locked || data.legacy_vehicle_rules.length > 0}
              onClick={() => void save("set_global", { company_percentage: globalRate })}>Save global commission</button>
          </section>

          <section className="space-y-4 rounded-xl border p-4" aria-labelledby="individual-commission-title">
            <h3 id="individual-commission-title" className="text-lg font-bold">Driver Commission Exceptions</h3>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium">{editingException ? "Edit an individual exception" : "Available driver"}
                <select className={inputClass} value={driverId} disabled={locked} onChange={(event) => setDriverId(event.target.value)}>
                  <option value="">Select a driver</option>
                  {availableExceptions.map((driver) => <option key={driver.id} value={driver.id}>{driver.name} (#{driver.id})</option>)}
                </select>
              </label>
              <label className="text-sm font-medium">ACT commission deducted (%)
                <input className={inputClass} type="number" min="0" max="100" step="0.01" inputMode="decimal"
                  value={individualRate} disabled={locked} onChange={(event) => setIndividualRate(event.target.value)} />
              </label>
            </div>
            <button type="button" className={buttonClass} disabled={locked || !driverId}
              onClick={() => void save("set_individual", { driver_ids: [Number(driverId)], company_percentage: individualRate })}>Save driver exception</button>
            {editingException && <button type="button" className="ml-3 underline" onClick={() => { setEditingException(false); setDriverId(""); setIndividualRate(""); }}>Cancel editing</button>}
            <div className="overflow-x-auto"><table className="w-full text-left text-sm">
              <caption className="sr-only">Drivers with individual commission exceptions</caption>
              <thead><tr><th className="p-2">Driver</th><th>ACT deduction</th><th>Driver share</th><th>Actions</th></tr></thead>
              <tbody>{lists.individual.map((driver) => <tr key={driver.id} className="border-t">
                <td className="p-2">{driver.name} (#{driver.id})</td><td>{driver.company_percentage}%</td><td>{driver.driver_percentage}%</td>
                <td className="space-x-3"><button type="button" disabled={locked} className="underline disabled:opacity-40" onClick={() => { setEditingException(true); setDriverId(String(driver.id)); setIndividualRate(driver.company_percentage); }}>Edit</button>
                  <button type="button" disabled={locked} className="underline disabled:opacity-40" onClick={() => void save("clear_individual", { driver_ids: [driver.id] })}>Return to global</button></td>
              </tr>)}</tbody>
            </table>{lists.individual.length === 0 && <p className="p-2 text-gray-500">No individual exceptions.</p>}</div>
          </section>

          <section className="space-y-4 rounded-xl border p-4" aria-labelledby="group-commission-title">
            <h3 id="group-commission-title" className="text-lg font-bold">Driver Commission Groups</h3>
            <label className="block text-sm font-medium">Create or manage a group
              <select className={inputClass} value={groupId} disabled={locked} onChange={(event) => {
                const value = event.target.value; setGroupId(value); setMemberIds([]);
                setGroupRate(data.groups.find((group) => group.id === Number(value))?.company_percentage ?? "");
              }}><option value="">Create a new group</option>
                {data.groups.map((group) => <option key={group.id} value={group.id}>{group.name}{group.is_active ? "" : " (inactive)"}</option>)}
              </select>
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              {!selectedGroup && <label className="text-sm font-medium">Group name
                <input className={inputClass} value={groupName} maxLength={120} disabled={locked} onChange={(event) => setGroupName(event.target.value)} placeholder="For example, DSS" />
              </label>}
              <label className="text-sm font-medium">ACT commission deducted (%)
                <input className={inputClass} type="number" min="0" max="100" step="0.01" inputMode="decimal" value={groupRate}
                  disabled={locked || Boolean(selectedGroup && !selectedGroup.is_active)} onChange={(event) => setGroupRate(event.target.value)} />
              </label>
            </div>
            <label className="block text-sm font-medium">Available drivers — select one or more
              <select multiple size={Math.min(6, Math.max(3, lists.global.length))} className={inputClass}
                value={memberIds} disabled={locked || Boolean(selectedGroup && !selectedGroup.is_active)}
                onChange={(event) => setMemberIds(Array.from(event.target.selectedOptions, (option) => option.value))}>
                {lists.global.map((driver) => <option key={driver.id} value={driver.id}>{driver.name} (#{driver.id})</option>)}
              </select>
            </label>
            {!selectedGroup ? <button type="button" className={buttonClass} disabled={locked || !groupName.trim() || memberIds.length === 0}
              onClick={() => void save("create_group", { name: groupName.trim(), company_percentage: groupRate, driver_ids: memberIds.map(Number) })}>Create group</button>
              : <div className="flex flex-wrap gap-3">
                <button type="button" className={buttonClass} disabled={locked || !selectedGroup.is_active}
                  onClick={() => void save("set_group_rate", { group_id: selectedGroup.id, company_percentage: groupRate })}>Save group commission</button>
                <button type="button" className={buttonClass} disabled={locked || !selectedGroup.is_active || memberIds.length === 0}
                  onClick={() => void save("add_members", { group_id: selectedGroup.id, driver_ids: memberIds.map(Number) })}>Add selected drivers</button>
              </div>}
            <div className="overflow-x-auto"><table className="w-full text-left text-sm">
              <caption className="sr-only">Commission groups and member counts</caption>
              <thead><tr><th className="p-2">Group</th><th>ACT deduction</th><th>Drivers</th></tr></thead>
              <tbody>{data.groups.map((group) => <tr key={group.id} className="border-t"><td className="p-2">{group.name}{group.is_active ? "" : " (inactive)"}</td><td>{group.company_percentage}%</td><td>{lists.grouped.filter((driver) => driver.group_id === group.id).length}</td></tr>)}</tbody>
            </table>{data.groups.length === 0 && <p className="p-2 text-gray-500">No commission groups.</p>}</div>
            {selectedGroup && ownMembers.map((driver) => <div key={driver.id} className="flex flex-wrap items-center justify-between gap-2 border-t py-2 text-sm">
              <span>{driver.name} (#{driver.id}) · ACT {driver.company_percentage}%</span>
              <button type="button" className="underline disabled:opacity-40" disabled={locked}
                onClick={() => void save("release_members", { group_id: selectedGroup.id, driver_ids: [driver.id] })}>Return to global</button>
            </div>)}
          </section>
        </>}
      </div>}
    </section>
  );
}
