
import { Elements } from "@stripe/react-stripe-js";
import { loadStripe, type StripeElementsOptions } from "@stripe/stripe-js";
import { ReactNode } from "react";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export default function StripeWrapper({ clientSecret, children, locale = "en" }: { clientSecret: string; children: ReactNode; locale?: "en" | "ar" | "fr" | "de" | "es" | "tr" | "zh-CN" }) {
  const appearance = {
    theme: "flat",
  };
  const options: StripeElementsOptions = {
    clientSecret,
    locale: locale === "zh-CN" ? "zh" : locale,
  };
  if (!clientSecret) return null;

  return (
    <Elements stripe={stripePromise} options={options}>
      {children}
    </Elements>
  );
}

