"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import type { Locale } from "../../../../i18n.config";
import { isPreparedPayment, readCheckoutTerms, sameTerms, termsAcknowledgement,
  type PreparedPayment, type TermsAcknowledgement, type TermsDescriptor, type TermsDocument } from "@/lib/checkout-terms";

// Per mounted booking only: no local/session storage, cookies, or module-global consent.
type Session = { key: string; locale: Locale; document: TermsDescriptor; response: PreparedPayment };
type SessionContext = { session: Session | null; save: (session: Session) => void;
  uncertain: boolean; hold: () => void };
const Context = createContext<SessionContext | null>(null);

export function CheckoutTermsProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [uncertain, setUncertain] = useState(false);
  return <Context.Provider value={{ session, save: setSession, uncertain, hold: () => setUncertain(true) }}>{children}</Context.Provider>;
}

export function useCheckoutTermsSession() {
  const context = useContext(Context);
  if (!context) throw new Error("Checkout terms require the booking context");
  return context;
}

// UI translations only; never translations or summaries of a legal document.
const copy = {
  en: ["Booking terms", "Download these terms (PDF)", "I agree to these booking terms, including the cancellation and refund conditions.", "Loading booking terms…", "Booking terms could not be verified. Payment has not been started.", "Reload terms", "The terms or booking details changed. Review them and agree again.", "Payment preparation could not be confirmed. Do not submit again; contact ACT support.", "Terms agreed for this payment", "The terms for this payment are unavailable. Do not pay; contact ACT support.", "Cancellation and refund conditions are set out in the booking terms."],
  ar: ["شروط الحجز", "تنزيل هذه الشروط (PDF)", "أوافق على شروط الحجز هذه، بما فيها شروط الإلغاء والاسترداد.", "جارٍ تحميل شروط الحجز…", "تعذر التحقق من شروط الحجز. لم يبدأ الدفع.", "إعادة تحميل الشروط", "تغيرت الشروط أو تفاصيل الحجز. يرجى مراجعتها والموافقة مجدداً.", "تعذر تأكيد إعداد الدفع. لا ترسل الطلب مجدداً؛ تواصل مع دعم ACT.", "الشروط المتفق عليها لهذا الدفع", "شروط هذا الدفع غير متاحة. لا تدفع؛ تواصل مع دعم ACT.", "ترد شروط الإلغاء والاسترداد في شروط الحجز."],
  fr: ["Conditions de réservation", "Télécharger ces conditions (PDF)", "J’accepte ces conditions de réservation, y compris les conditions d’annulation et de remboursement.", "Chargement des conditions…", "Impossible de vérifier les conditions. Le paiement n’a pas été démarré.", "Recharger les conditions", "Les conditions ou les détails ont changé. Vérifiez-les et acceptez-les à nouveau.", "La préparation du paiement n’a pas pu être confirmée. Ne renvoyez pas la demande ; contactez ACT.", "Conditions acceptées pour ce paiement", "Les conditions de ce paiement sont indisponibles. Ne payez pas ; contactez ACT.", "Les conditions d’annulation et de remboursement figurent dans les conditions de réservation."],
  de: ["Buchungsbedingungen", "Diese Bedingungen herunterladen (PDF)", "Ich akzeptiere diese Buchungsbedingungen einschließlich der Stornierungs- und Erstattungsbedingungen.", "Buchungsbedingungen werden geladen…", "Die Bedingungen konnten nicht geprüft werden. Die Zahlung wurde nicht gestartet.", "Bedingungen neu laden", "Bedingungen oder Buchungsdaten wurden geändert. Bitte erneut prüfen und zustimmen.", "Die Zahlungsvorbereitung konnte nicht bestätigt werden. Nicht erneut absenden; ACT kontaktieren.", "Für diese Zahlung akzeptierte Bedingungen", "Die Bedingungen für diese Zahlung fehlen. Nicht bezahlen; ACT kontaktieren.", "Stornierungs- und Erstattungsregeln stehen in den Buchungsbedingungen."],
  es: ["Condiciones de reserva", "Descargar estas condiciones (PDF)", "Acepto estas condiciones de reserva, incluidas las condiciones de cancelación y reembolso.", "Cargando las condiciones…", "No se pudieron verificar las condiciones. No se ha iniciado el pago.", "Volver a cargar", "Han cambiado las condiciones o la reserva. Revísalas y vuelve a aceptarlas.", "No se pudo confirmar la preparación del pago. No vuelvas a enviarlo; contacta con ACT.", "Condiciones aceptadas para este pago", "Las condiciones de este pago no están disponibles. No pagues; contacta con ACT.", "Las condiciones de cancelación y reembolso figuran en las condiciones de reserva."],
  tr: ["Rezervasyon koşulları", "Bu koşulları indir (PDF)", "İptal ve iade koşulları dahil bu rezervasyon koşullarını kabul ediyorum.", "Koşullar yükleniyor…", "Koşullar doğrulanamadı. Ödeme başlatılmadı.", "Koşulları yeniden yükle", "Koşullar veya rezervasyon değişti. İnceleyip yeniden kabul edin.", "Ödeme hazırlığı doğrulanamadı. Tekrar göndermeyin; ACT desteğiyle iletişime geçin.", "Bu ödeme için kabul edilen koşullar", "Bu ödemenin koşulları mevcut değil. Ödeme yapmayın; ACT ile iletişime geçin.", "İptal ve iade koşulları rezervasyon koşullarında yer alır."],
  zh: ["预订条款", "下载这些条款（PDF）", "我同意这些预订条款，包括取消和退款条件。", "正在加载预订条款…", "无法核实预订条款。尚未发起付款。", "重新加载条款", "条款或预订信息已更改。请重新查看并同意。", "无法确认付款准备结果。请勿再次提交，请联系 ACT 客服。", "本次付款已同意的条款", "本次付款的条款不可用。请勿付款，请联系 ACT 客服。", "取消和退款条件载于预订条款。"],
} satisfies Record<Locale, readonly string[]>;
export function checkoutTermsText(locale: Locale, index: number) { return copy[locale][index]; }

export function TermsDocumentView({ document, final = false }: { document: TermsDocument; final?: boolean }) {
  return <section id={final ? "act-payment-terms" : "act-review-terms"} lang={document.locale}
    dir={document.locale === "ar" ? "rtl" : "ltr"} className="min-w-0 rounded-xl border border-white/30 p-4 text-white space-y-3">
    <h3 className="font-semibold">{checkoutTermsText(document.locale, final ? 8 : 0)}</h3>
    <p className="text-sm break-all">{document.terms_version}</p>
    <div role="region" aria-label={checkoutTermsText(document.locale, 0)} tabIndex={0}
      className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-sm leading-6 border border-white/20 rounded-lg p-3"
      style={{ overflowWrap: "anywhere" }}>{document.text}</div>
    <a className="inline-block text-[#ffd100] underline py-2" href={document.document_url}
      target="_blank" rel="noopener noreferrer">{checkoutTermsText(document.locale, 1)}</a>
  </section>;
}

type View = { key: string; document: TermsDescriptor | null; error: boolean };
export function useCheckoutTerms(locale: Locale, booking: unknown, token?: string) {
  const context = useCheckoutTermsSession();
  const key = JSON.stringify([locale, booking, token || ""]);
  const current = useRef(key); current.current = key;
  const generation = useRef(0);
  const inFlight = useRef(false);
  const agreement = useRef(false);
  const [agreed, setAgreed] = useState(false);
  const [reload, setReload] = useState(0);
  const [notice, setNotice] = useState(false);
  const [view, setView] = useState<View>({ key, document: null, error: false });
  const session = context.session;

  useEffect(() => {
    const mine = ++generation.current;
    agreement.current = false; setAgreed(false); setNotice(false);
    setView({ key, document: null, error: false });
    // Returning without changing the booking reuses its prepared payment and the
    // same accepted document. Never replace it with a newer public release.
    const read = session?.key === key ? Promise.resolve(session.document) : readCheckoutTerms(locale);
    read.then(document => {
      if (generation.current === mine && current.current === key) setView({ key, document, error: false });
    }).catch(() => {
      if (generation.current === mine && current.current === key) setView({ key, document: null, error: true });
    });
    return () => { generation.current++; };
    // Session is intentionally read only on entry/booking change, not after save.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, reload]);

  const document = view.key === key ? view.document : null;
  const ready = !context.uncertain && !!document && (!document.enabled || (agreed && agreement.current));
  const choose = (value: boolean) => { agreement.current = value; setAgreed(value); };
  async function prepare(post: (ack: TermsAcknowledgement | undefined) => Promise<unknown>): Promise<PreparedPayment | null> {
    if (inFlight.current || !ready || !document) return null;
    inFlight.current = true;
    const entry = key;
    const mine = generation.current;
    let posted = false;
    try {
      if (session?.key === entry && sameTerms(document, session.document)) return session.response;
      const fresh = await readCheckoutTerms(locale);
      if (current.current !== entry || generation.current !== mine) return null;
      if (!sameTerms(document, fresh)) {
        choose(false); setNotice(true); setView({ key: entry, document: fresh, error: false });
        return null;
      }
      if (fresh.enabled && !agreement.current) return null;
      posted = true;
      const response = await post(termsAcknowledgement(fresh));
      if (!isPreparedPayment(response) || current.current !== entry || generation.current !== mine) {
        context.hold(); return null;
      }
      context.save({ key: entry, locale, document: fresh, response });
      return response;
    } catch {
      if (posted) context.hold(); // Unknown POST outcome: never automatically send again.
      else if (current.current === entry) setView({ key: entry, document: null, error: true });
      return null;
    } finally { inFlight.current = false; }
  }
  // Read the guard synchronously: a second same-tick click must not return to
  // the outer handler and clear its busy state while the first POST is pending.
  return { document, get ready() { return ready && !inFlight.current; },
    agreed: agreed && view.key === key, choose, prepare,
    error: view.key === key && view.error, notice, uncertain: context.uncertain,
    retry: () => { if (!inFlight.current) { choose(false); setReload(x => x + 1); } } };
}

export function CheckoutTermsConsent({ gate, locale, disabled }: {
  gate: ReturnType<typeof useCheckoutTerms>; locale: Locale; disabled: boolean;
}) {
  if (gate.uncertain) return <p role="alert" className="rounded-xl border border-red-300 p-4 text-white">{checkoutTermsText(locale, 7)} <a href="mailto:info@airportandcitytransfer.com" className="underline">info@airportandcitytransfer.com</a></p>;
  if (gate.error) return <div role="alert" className="rounded-xl border border-red-300 p-4 text-white">
    <p>{checkoutTermsText(locale, 4)}</p><button type="button" disabled={disabled} onClick={gate.retry}
      className="mt-3 min-h-11 rounded-lg border border-[#ffd100] px-4 py-2">{checkoutTermsText(locale, 5)}</button></div>;
  if (!gate.document) return <p role="status" className="text-white">{checkoutTermsText(locale, 3)}</p>;
  if (!gate.document.enabled) return null;
  return <div className="space-y-3">
    {gate.notice && <p role="alert" className="text-[#ffd100]">{checkoutTermsText(locale, 6)}</p>}
    <TermsDocumentView document={gate.document} />
    <label className="flex items-start gap-3 rounded-xl border border-white/20 p-4 text-white text-sm leading-6 cursor-pointer">
      <input type="checkbox" checked={gate.agreed} disabled={disabled} onChange={e => gate.choose(e.target.checked)}
        className="mt-1 h-5 w-5 shrink-0 accent-[#ffd100]" />
      <span>{checkoutTermsText(locale, 2)}</span>
    </label>
  </div>;
}
