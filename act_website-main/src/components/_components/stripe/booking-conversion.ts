declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}

const GOOGLE_ADS_ID = process.env.NEXT_PUBLIC_GOOGLE_ADS_ID || "AW-17641563982";
const CONVERSION_LABEL = process.env.NEXT_PUBLIC_GOOGLE_ADS_BOOKING_CONVERSION_LABEL || "0LprCMbR8sQcEM7Ok9xB";
const SEND_TO = "AW-17641563982/0LprCMbR8sQcEM7Ok9xB";
const STORAGE_PREFIX = "act_booking_conversion_tracked";
const EVENT_TIMEOUT = 2000;
const GTAG_WAIT_TIMEOUT = 3000;
const trackedIds = new Set<string>();

async function waitForGtag() {
  const startedAt = Date.now();
  while (typeof window.gtag !== "function" && Date.now() - startedAt < GTAG_WAIT_TIMEOUT) {
    await new Promise((resolve) => window.setTimeout(resolve, 100));
  }
  return window.gtag;
}

export async function fireBookingCompletedConversion(transactionId: string, bookingTotal: number) {
  if (!transactionId || !GOOGLE_ADS_ID || !CONVERSION_LABEL || trackedIds.has(transactionId)) return;
  const storageKey = `${STORAGE_PREFIX}:${transactionId}`;
  try {
    if (window.sessionStorage.getItem(storageKey)) return;
  } catch {}

  if (typeof window === "undefined") return;
  const gtag = await waitForGtag();
  if (typeof gtag !== "function") return;
  trackedIds.add(transactionId);

  await new Promise<void>((resolve) => {
    let completed = false;
    const complete = () => {
      if (completed) return;
      completed = true;
      window.clearTimeout(timeoutId);
      try {
        window.sessionStorage.setItem(storageKey, "1");
      } catch {}
      resolve();
    };
    const timeoutId = window.setTimeout(complete, EVENT_TIMEOUT + 250);
    try {
      gtag("event", "conversion", {
        send_to: SEND_TO,
        value: Number.isFinite(bookingTotal) ? bookingTotal : 0,
        currency: "GBP",
        transaction_id: transactionId,
        event_callback: complete,
        event_timeout: EVENT_TIMEOUT,
      });
    } catch {
      complete();
    }
  });
}
