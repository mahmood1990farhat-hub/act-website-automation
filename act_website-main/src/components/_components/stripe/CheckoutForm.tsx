"use client";
import { customerPaymentError, runtimeText } from "@/lib/customer-runtime";

import {
  CardNumberElement,
  CardExpiryElement,
  CardCvcElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { Button } from "@/components/ui/button";
import { useRef, useState } from "react";
import Image from "next/image";
import { FaArrowLeft } from "react-icons/fa";
import MoneyCountingHand from "../loading/MoneyCountingHand";
import Policy from "../Policy";
import Terms from "../Terms";
import { languageType, Locale } from "../../../../i18n.config";

declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}

const ELEMENT_OPTIONS = {
  style: {
    base: {
      fontSize: "16px",
      color: "#18181A",
      "::placeholder": {
        color: "#364153",
      },
    },
    invalid: {
      color: "#ef4444",
    },
  },
};

const GOOGLE_ADS_ID =
  process.env.NEXT_PUBLIC_GOOGLE_ADS_ID || "AW-17641563982";
const GOOGLE_ADS_BOOKING_CONVERSION_LABEL =
  process.env.NEXT_PUBLIC_GOOGLE_ADS_BOOKING_CONVERSION_LABEL ||
  "0LprCMbR8sQcEM7Ok9xB";
const GOOGLE_ADS_BOOKING_CONVERSION_SEND_TO =
  "AW-17641563982/0LprCMbR8sQcEM7Ok9xB";
const EXPECTED_GOOGLE_ADS_BOOKING_CONVERSION_LABEL =
  "0LprCMbR8sQcEM7Ok9xB";
const BOOKING_CONVERSION_STORAGE_PREFIX = "act_booking_conversion_tracked";
const BOOKING_CONVERSION_EVENT_TIMEOUT = 2000;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
const BOOKING_STATUS_ATTEMPTS = 30;
const BOOKING_STATUS_INTERVAL_MS = 1000;

export default function CheckoutForm({
  nextStep,
  prevStep,
  clientSecret,
  bookingTotal,
  currency,
  trans,
  policy_and_terms,
  locale = "en" as languageType
}: {
  nextStep: () => void;
  prevStep: () => void;
  trans: any;
  clientSecret: string;
  bookingTotal: number;
  currency: string;
  policy_and_terms:any;
  locale?: Locale;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [cardComplete, setCardComplete] = useState(false);
  const [expiryComplete, setExpiryComplete] = useState(false);
  const [cvcComplete, setCvcComplete] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [paymentCaptured, setPaymentCaptured] = useState(false);
  const [fulfillmentMsg, setFulfillmentMsg] = useState("");
  const trackedPaymentIntentIds = useRef<Set<string>>(new Set());

  const fireBookingCompletedEvents = (transactionId: string): Promise<void> => {
    console.info("[ACT Google Ads] conversion function entered", {
      transaction_id: transactionId,
    });

    return new Promise((resolve) => {
      const finish = (reason: "callback" | "timeout" | "skipped") => {
        console.info(`[ACT Google Ads] conversion ${reason}`, {
          transaction_id: transactionId,
        });
        resolve();
      };

      if (!transactionId || !GOOGLE_ADS_ID || !GOOGLE_ADS_BOOKING_CONVERSION_LABEL) {
        console.info("[ACT Google Ads] conversion skipped: missing config", {
          hasTransactionId: Boolean(transactionId),
          hasGoogleAdsId: Boolean(GOOGLE_ADS_ID),
          hasConversionLabel: Boolean(GOOGLE_ADS_BOOKING_CONVERSION_LABEL),
        });
        finish("skipped");
        return;
      }

      if (trackedPaymentIntentIds.current.has(transactionId)) {
        console.info("[ACT Google Ads] conversion skipped: in-memory duplicate", {
          transaction_id: transactionId,
        });
        finish("skipped");
        return;
      }

      const storageKey = `${BOOKING_CONVERSION_STORAGE_PREFIX}:${transactionId}`;

      const gtag = typeof window !== "undefined" ? window.gtag : undefined;
      const gtagAvailable = typeof gtag === "function";

      console.info("[ACT Google Ads] window.gtag availability", {
        available: gtagAvailable,
        send_to: GOOGLE_ADS_BOOKING_CONVERSION_SEND_TO,
      });

      if (!gtagAvailable) {
        console.info("[ACT Google Ads] conversion skipped: window.gtag unavailable", {
          transaction_id: transactionId,
        });
        finish("skipped");
        return;
      }

      console.info("[ACT Google Ads] conversion label comparison", {
        runtimeLabel: GOOGLE_ADS_BOOKING_CONVERSION_LABEL,
        expectedLabel: EXPECTED_GOOGLE_ADS_BOOKING_CONVERSION_LABEL,
        matchesExpected:
          GOOGLE_ADS_BOOKING_CONVERSION_LABEL ===
          EXPECTED_GOOGLE_ADS_BOOKING_CONVERSION_LABEL,
      });

      let sessionStorageAlreadyTracked = false;
      try {
        sessionStorageAlreadyTracked = Boolean(
          window.sessionStorage.getItem(storageKey),
        );
        console.info("[ACT Google Ads] sessionStorage duplicate check", {
          storageKey,
          alreadyTracked: sessionStorageAlreadyTracked,
        });
        if (sessionStorageAlreadyTracked) {
          console.info("[ACT Google Ads] conversion skipped: session duplicate", {
            transaction_id: transactionId,
          });
          finish("skipped");
          return;
        }
      } catch (error) {
        console.info("[ACT Google Ads] sessionStorage duplicate check failed", {
          storageKey,
          error,
        });
        // Ignore storage access issues and still track the successful payment once per component lifecycle.
      }

      trackedPaymentIntentIds.current.add(transactionId);

      let hasCompleted = false;
      const completeOnce = (reason: "callback" | "timeout") => {
        if (hasCompleted) return;
        hasCompleted = true;
        window.clearTimeout(timeoutId);

        try {
          window.sessionStorage.setItem(storageKey, "1");
        } catch {
          // Storage is best-effort duplicate protection; the in-memory guard still prevents double submits.
        }

        console.info("[ACT Google Ads] callback/timeout completed", {
          reason,
          transaction_id: transactionId,
        });
        finish(reason);
      };

      const timeoutId = window.setTimeout(() => {
        completeOnce("timeout");
      }, BOOKING_CONVERSION_EVENT_TIMEOUT + 250);

      const conversionPayload: Record<string, string | number | (() => void)> = {
        send_to: GOOGLE_ADS_BOOKING_CONVERSION_SEND_TO,
        value: Number.isFinite(Number(bookingTotal)) ? Number(bookingTotal) : 0,
        currency: "GBP",
        transaction_id: transactionId,
        event_callback: () => completeOnce("callback"),
        event_timeout: BOOKING_CONVERSION_EVENT_TIMEOUT,
      };

      console.info("[ACT Google Ads] sending conversion", {
        send_to: GOOGLE_ADS_BOOKING_CONVERSION_SEND_TO,
        transaction_id: transactionId,
      });

      try {
        console.info("[ACT Google Ads] before gtag conversion call", {
          send_to: conversionPayload.send_to,
          transaction_id: transactionId,
          value: conversionPayload.value,
          currency: conversionPayload.currency,
        });
        gtag("event", "conversion", conversionPayload);
        console.info("[ACT Google Ads] after gtag conversion call", {
          transaction_id: transactionId,
        });
      } catch (error) {
        console.error("[ACT Google Ads] conversion gtag call failed", error);
        completeOnce("timeout");
      }
    });
  };


  const waitForBookingConfirmation = async (paymentIntentId: string) => {
    if (!API_BASE_URL) return false;

    for (let attempt = 0; attempt < BOOKING_STATUS_ATTEMPTS; attempt += 1) {
      try {
        const query = new URLSearchParams({ payment_intent_id: paymentIntentId });
        const response = await fetch(
          API_BASE_URL + "/api/payments/booking-status/?" + query.toString(),
          { method: "GET", cache: "no-store" },
        );
        if (response.ok) {
          const body = await response.json();
          if (body?.status === "confirmed") return true;
        }
      } catch {
        // A transient status-check failure must never invite a second payment.
      }

      await new Promise((resolve) =>
        window.setTimeout(resolve, BOOKING_STATUS_INTERVAL_MS),
      );
    }

    return false;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements || paymentCaptured) return;

    setLoading(true);
    setErrorMsg("");
    setFulfillmentMsg("");

    const card = elements.getElement(CardNumberElement);
    let stripePaymentSucceeded = false;

    try {
      const result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: card!,
        },
      });

      if (result.error) {
        setErrorMsg(customerPaymentError(locale, result.error));
        return;
      }

      if (result.paymentIntent.status === "succeeded") {
        stripePaymentSucceeded = true;
        setPaymentCaptured(true);
        setFulfillmentMsg(runtimeText(locale, "bookingFinalising"));

        const bookingConfirmed = await waitForBookingConfirmation(
          result.paymentIntent.id,
        );

        if (bookingConfirmed) {
          await fireBookingCompletedEvents(result.paymentIntent.id);
          nextStep();
          return;
        }

        setFulfillmentMsg(runtimeText(locale, "bookingFinalisingDelayed"));
      }
    } catch {
      if (stripePaymentSucceeded) {
        setPaymentCaptured(true);
        setFulfillmentMsg(runtimeText(locale, "bookingFinalisingDelayed"));
      } else {
        setErrorMsg(runtimeText(locale, "paymentUnknown"));
      }
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = cardComplete && expiryComplete && cvcComplete && agreed;

  return (
    <div>
      <h1 className="text-center text-4xl font-semibold mb-2 text-white">
        {trans.title}
      </h1>

      <p className="text-sm text-center text-muted mb-5">{trans.subtitle}</p>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {/* Card Number */}
        <div>
          <label>
            <p>{trans.form.Card_Number}</p>
          </label>
          <div className="p-3 border-2 bg-white text-foreground border-muted rounded-lg">
            <CardNumberElement
              onChange={(event) => setCardComplete(event.complete)}
              options={{
                style: {
                  base: {
                    fontSize: "16px",
                    color: "#18181A",
                    "::placeholder": {
                      color: "#364153",
                    },
                  },
                  invalid: {
                    color: "#ef4444",
                  },
                },
                showIcon: true, // هذا الخيار يُفعل ظهور الأيقونة الافتراضية
              }}
              className="w-full"
            />
          </div>
        </div>

        {/* Expiry & CVC */}
        <div className="flex items-center justify-between max-md:flex-col gap-4">
          <div className="w-full">
            <label>
              <p>{trans.form.Expired_date}</p>
            </label>
            <div className="w-full p-2.5 border-2 bg-white text-foreground border-muted rounded-lg">
              <CardExpiryElement
                options={ELEMENT_OPTIONS}
                onChange={(event) => setExpiryComplete(event.complete)}
                className="w-full"
              />
            </div>
          </div>
          <div className="w-full">
            <label>
              <p>{runtimeText(locale, "cvc")}</p>
            </label>
            <div className="w-full p-2.5 border-2 bg-white text-foreground border-muted rounded-lg">
              <CardCvcElement
                onChange={(event) => setCvcComplete(event.complete)}
                options={ELEMENT_OPTIONS}
                className="w-full"
              />
            </div>
          </div>
        </div>

        {/* Agreement */}
        <div>
          <div className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              className="accent-primary w-4 h-4 cursor-pointer"
              onChange={(e) => setAgreed(e.target.checked)}
            />
            <div className="space-x-1 flex items-center  select-none">
              <span>{trans.form.check.Agree}</span>
              <span className="text-primary ">
                <Policy trans={policy_and_terms.policy} locale={locale}/>

              </span>
              <span> & </span>
              <span className="text-primary">
            <Terms trans={policy_and_terms.terms} locale={locale}/>
              </span>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {errorMsg && <p role="alert" className="text-red-500 text-sm">{errorMsg}</p>}
        {fulfillmentMsg && <p role="status" className="rounded-lg border border-[#ffd100]/40 bg-[#ffd100]/10 p-3 text-sm text-white">{fulfillmentMsg}</p>}

        {/* Buttons */}
        <div className="flex items-center gap-2" dir="ltr">
          <Button
            onClick={prevStep}
            type="button"
            disabled={loading || paymentCaptured}
            className="w-1/6 border border-primary bg-transparent hover:text-black hover:bg-primary text-primary p-6 cursor-pointer"
          >
            <FaArrowLeft className="text-3xl" />
          </Button>
          <div className="w-full">
            <Button
              type="submit"
              disabled={!isFormValid || loading || paymentCaptured}
              className="w-full text-lg p-6 cursor-pointer"
            >
              {loading ? <div><MoneyCountingHand/></div>: trans.form.button}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

