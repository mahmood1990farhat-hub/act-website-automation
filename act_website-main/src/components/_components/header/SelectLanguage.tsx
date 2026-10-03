"use client";
import { LANGUAGE_CHANGE_EVENT, clearLanguageDraft } from "@/lib/booking-language-draft";
import { languageSwitchText } from "@/lib/language-switch-text";
import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import { TbWorld } from "react-icons/tb";
import { enabledLocales, localeRegistry, localizedPath, type Locale, type SupportedLocale } from "../../../../i18n.config";

export default function SelectLanguage({ locale, language }: {
  locale: string; language: { English: string; Arabic: string };
}) {
  const [open, setOpen] = useState(false);
  const [switchError, setSwitchError] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const label = (code: SupportedLocale) => code === "en" ? language.English : code === "ar" ? language.Arabic : localeRegistry[code].label;
  useEffect(() => {
    const close = (event: MouseEvent) => { if (!ref.current?.contains(event.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  useEffect(() => setOpen(false), [pathname]);
  return <div ref={ref} className="relative" onKeyDown={e => { if (e.key === "Escape") setOpen(false); }}>
    <button type="button" aria-label={languageSwitchText(locale, "choose")}
      aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}
      className="flex items-center gap-2 px-4 py-2.5 bg-primary/10 text-primary rounded-lg border border-primary/30">
      <TbWorld /><span>{localeRegistry[locale as Locale]?.label || "English"}</span>
    </button>
    {switchError && <p role="alert" className="absolute end-0 z-50 mt-2 w-72 bg-black p-3 text-white">{switchError}</p>}
    {open && <ul className="absolute end-0 z-50 mt-2 min-w-36 p-2 rounded border border-primary/30 bg-black text-primary">
      {enabledLocales.map(code => <li key={code}><button type="button" lang={code}
        aria-current={code === locale ? "true" : undefined}
        className="w-full rounded p-2 text-start hover:bg-white/10"
        onClick={() => {
          setSwitchError("");
          if (code === locale) { setOpen(false); return; }
          const detail = { locale: code, reason: "failed" as "failed" | "payment" };
          const event = new CustomEvent(LANGUAGE_CHANGE_EVENT, { cancelable: true, detail });
          if (!window.dispatchEvent(event)) {
            try { clearLanguageDraft(window.sessionStorage); } catch {}
            setOpen(false);
            setSwitchError(languageSwitchText(locale, detail.reason));
            return;
          }
          setOpen(false);
          window.location.assign(localizedPath(pathname, code) + window.location.search + window.location.hash);
        }}>
        {label(code)}
      </button></li>)}
    </ul>}
  </div>;
}

