"use client";

import { PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";
import { useState } from "react";
import { FaArrowLeft } from "react-icons/fa";
import { Button } from "@/components/ui/button";
import MoneyCountingHand from "../loading/MoneyCountingHand";
import Policy from "../Policy";
import Terms from "../Terms";
import { languageType, Locale } from "../../../../i18n.config";
import { fireBookingCompletedConversion } from "./booking-conversion";

export default function CheckoutForm({
  nextStep,
  prevStep,
  clientSecret,
  bookingTotal,
  trans,
  policy_and_terms,
  locale = "en" as languageType,
}: {
  nextStep: () => void;
  prevStep: () => void;
  trans: any;
  clientSecret: string;
  bookingTotal: number;
  currency: string;
  policy_and_terms: any;
  locale?: Locale;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [paymentComplete, setPaymentComplete] = useState(false);
  const [agreed, setAgreed] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!stripe || !elements) return;

    setLoading(true);
    setErrorMsg("");
    const result = await stripe.confirmPayment({
      elements,
      clientSecret,
      confirmParams: {
        return_url: `${window.location.origin}/${locale}/payment-return`,
      },
      redirect: "if_required",
    });

    if (result.error) {
      setErrorMsg(result.error.message || "Payment failed");
    } else if (result.paymentIntent.status === "succeeded") {
      await fireBookingCompletedConversion(result.paymentIntent.id, bookingTotal);
      nextStep();
    } else if (result.paymentIntent.status === "processing") {
      setErrorMsg("Your payment is processing. We will confirm your booking when payment completes.");
    } else {
      setErrorMsg("Payment was not completed. Please choose a payment method and try again.");
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="mb-2 text-center text-4xl font-semibold text-white">{trans.title}</h1>
      <p className="mb-5 text-center text-sm text-muted">{trans.subtitle}</p>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="rounded-md bg-white p-3 text-foreground">
          <PaymentElement
            onChange={(event) => {
              setPaymentComplete(event.complete);
              if (event.complete) setErrorMsg("");
            }}
            options={{ layout: "tabs" }}
          />
        </div>

        <div className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            className="h-4 w-4 cursor-pointer accent-primary"
            onChange={(event) => setAgreed(event.target.checked)}
          />
          <div className="flex select-none items-center space-x-1">
            <span>{trans.form.check.Agree}</span>
            <span className="text-primary"><Policy trans={policy_and_terms.policy} locale={locale} /></span>
            <span> &amp; </span>
            <span className="text-primary"><Terms trans={policy_and_terms.terms} locale={locale} /></span>
          </div>
        </div>

        {errorMsg && <p className="text-sm text-red-500">{errorMsg}</p>}

        <div className="flex items-center gap-2" dir="ltr">
          <Button onClick={prevStep} type="button" className="w-1/6 cursor-pointer border border-primary bg-transparent p-6 text-primary hover:bg-primary hover:text-black">
            <FaArrowLeft className="text-3xl" />
          </Button>
          <Button type="submit" disabled={!paymentComplete || !agreed || loading} className="w-full cursor-pointer p-6 text-lg">
            {loading ? <MoneyCountingHand /> : trans.form.button}
          </Button>
        </div>
      </form>
    </div>
  );
}
