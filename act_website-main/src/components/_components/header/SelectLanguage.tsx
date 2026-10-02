"use client";
import { useState, useRef, useEffect } from "react";
import { usePathname } from "next/navigation";
import { TbWorld } from "react-icons/tb";
import { enabledLocales, localeRegistry, localizedPath, type Locale, type SupportedLocale } from "../../../../i18n.config";

export default function SelectLanguage({ locale, language }: {
  locale: string; language: { English: string; Arabic: string };
}) {
  const [open, setOpen] = useState(false);
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
    <button type="button" aria-label={locale === "ar" ? "اختر اللغة" : locale === "fr" ? "Choisir une langue" : "Choose language"}
      aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}
      className="flex items-center gap-2 px-4 py-2.5 bg-primary/10 text-primary rounded-lg border border-primary/30">
      <TbWorld /><span>{localeRegistry[locale as Locale]?.label || "English"}</span>
    </button>
    {open && <ul className="absolute end-0 z-50 mt-2 min-w-36 p-2 rounded border border-primary/30 bg-black text-primary">
      {enabledLocales.map(code => <li key={code}><button type="button" lang={code}
        aria-current={code === locale ? "true" : undefined}
        className="w-full rounded p-2 text-start hover:bg-white/10"
        onClick={() => { setOpen(false); if (code !== locale) window.location.assign(localizedPath(pathname, code) + window.location.search + window.location.hash); }}>
        {label(code)}
      </button></li>)}
    </ul>}
  </div>;
}

