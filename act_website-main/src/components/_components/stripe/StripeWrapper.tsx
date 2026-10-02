
import { Elements } from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { ReactNode } from "react";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export default function StripeWrapper({ clientSecret, children, locale = "en" }: { clientSecret: string; children: ReactNode; locale?: "en" | "ar" }) {
  const appearance = {
    theme: "flat",
  };
  const options = {
    clientSecret,
    locale,
  };
  if (!clientSecret) return null;

  return (
    <Elements stripe={stripePromise} options={options}>
      {children}
    </Elements>
  );
}
