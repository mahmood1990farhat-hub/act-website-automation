"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Locale } from "../../../../../i18n.config";

export default function DriverPasswordSetup({ locale }: { locale: Locale }) {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [email, setEmail] = useState("");
  const [working, setWorking] = useState(false);
  const [done, setDone] = useState(false);
  const [message, setMessage] = useState("");
  const api = process.env.NEXT_PUBLIC_API_BASE_URL || "";

  useEffect(() => {
    // The token arrives as a URL fragment: it is never sent in the initial
    // HTTP request or Referer. Remove it from browser history immediately.
    const value = window.location.hash.slice(1);
    setToken(value);
    window.history.replaceState(null, "", window.location.pathname);
  }, []);

  const setup = async (event: React.FormEvent) => {
    event.preventDefault();
    if (working) return;
    setMessage("");
    if (!token) { setMessage("The link is invalid. Request a new link below."); return; }
    if (password.length < 10 || password !== confirm) {
      setMessage("Choose matching passwords of at least 10 characters.");
      return;
    }
    setWorking(true);
    try {
      const response = await fetch(api + "/api/drivers/onboarding/set-password/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password, confirm_password: confirm }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to set your password.");
      setPassword(""); setConfirm(""); setToken("");
      setDone(true);
      setMessage("Password set. Your application is still pending ACT verification.");
    } catch (error: any) {
      setMessage(error?.message || "The link could not be used.");
    } finally { setWorking(false); }
  };

  const resend = async (event: React.FormEvent) => {
    event.preventDefault();
    if (working) return;
    setWorking(true); setMessage("");
    try {
      await fetch(api + "/api/drivers/onboarding/resend-password-link/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setMessage("If your application is eligible, a new link will be sent to your email.");
    } catch {
      setMessage("Please contact ACT support if the email does not arrive.");
    } finally { setWorking(false); }
  };

  return <main className="mx-auto my-12 max-w-xl rounded-xl border border-gray-700 bg-gray-900 p-6 text-white">
    <h1 className="mb-3 text-2xl font-bold text-yellow-400">ACT Driver — Set your password</h1>
    <p className="mb-6 text-sm">This enables your application portal. Driving and trip offers require separate ACT approval.</p>
    {done ? <Link className="font-semibold text-yellow-400 underline" href={`/${locale}/auth`}>
      Proceed to driver login
    </Link> : <form className="space-y-4" onSubmit={setup}>
      <label className="block text-sm">Password
        <input type="password" autoComplete="new-password" required minLength={10}
          className="mt-1 w-full rounded-lg border bg-white p-3 text-black"
          value={password} onChange={event => setPassword(event.target.value)} />
      </label>
      <label className="block text-sm">Confirm password
        <input type="password" autoComplete="new-password" required minLength={10}
          className="mt-1 w-full rounded-lg border bg-white p-3 text-black"
          value={confirm} onChange={event => setConfirm(event.target.value)} />
      </label>
      <button disabled={working} className="w-full rounded-lg bg-yellow-400 p-3 font-bold text-black disabled:opacity-50">
        {working ? "Processing..." : "Set up password"}
      </button>
    </form>}
    <form onSubmit={resend} className="mt-8 space-y-3 border-t border-gray-700 pt-5">
      <h2 className="text-lg font-semibold">Link expired or not received?</h2>
      <label className="block text-sm">Application email
        <input type="email" autoComplete="email" required
          className="mt-1 w-full rounded-lg border bg-white p-3 text-black"
          value={email} onChange={event => setEmail(event.target.value)} />
      </label>
      <button type="submit" disabled={working} className="rounded-lg border border-yellow-400 p-3 text-yellow-400 disabled:opacity-50">
        Resend setup link
      </button>
    </form>
    {message && <p role="status" className="mt-5 rounded-lg bg-gray-800 p-3 text-sm">{message}</p>}
  </main>;
}
