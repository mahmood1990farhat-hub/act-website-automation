"use client";

import {
  CardNumberElement,
  CardExpiryElement,
  CardCvcElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import Image from "next/image";
import { FaArrowLeft } from "react-icons/fa";
import MoneyCountingHand from "../loading/MoneyCountingHand";
import Policy from "../Policy";
import Terms from "../Terms";
import { languageType, Locale } from "../../../../i18n.config";

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

export default function CheckoutForm({
  nextStep,
  prevStep,
  clientSecret,
  trans,
  policy_and_terms,
  locale = "en" as languageType
}: {
  nextStep: () => void;
  prevStep: () => void;
  trans: any;
  clientSecret: string;
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) return;

    setLoading(true);
    setErrorMsg("");

    const card = elements.getElement(CardNumberElement);

    const result = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: card!,
      },
    });

    if (result.error) {
      setErrorMsg(result.error.message || "Payment failed");
    } else if (result.paymentIntent.status === "succeeded") {
      nextStep();
    }

    setLoading(false);
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
              <p>CVC</p>
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
        {errorMsg && <p className="text-red-500 text-sm">{errorMsg}</p>}

        {/* Buttons */}
        <div className="flex items-center gap-2" dir="ltr">
          <Button
            onClick={prevStep}
            type="button"
            className="w-1/6 border border-primary bg-transparent hover:text-black hover:bg-primary text-primary p-6 cursor-pointer"
          >
            <FaArrowLeft className="text-3xl" />
          </Button>
          <div className="w-full">
            <Button
              type="submit"
              disabled={!isFormValid || loading}
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
