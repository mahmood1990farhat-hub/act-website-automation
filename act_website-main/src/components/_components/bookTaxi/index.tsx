"use client";

import React from "react";
import BookingFlow from "./BookingFlow";
import { CheckoutTermsProvider } from "./CheckoutTerms";

// The original booking flow is preserved byte-for-byte in BookingFlow.tsx.
// Context keeps the accepted document within this booking across review/payment.
export * from "./BookingFlow";
export default function BookTaxi(props: React.ComponentProps<typeof BookingFlow>) {
  return <CheckoutTermsProvider><BookingFlow {...props} /></CheckoutTermsProvider>;
}
