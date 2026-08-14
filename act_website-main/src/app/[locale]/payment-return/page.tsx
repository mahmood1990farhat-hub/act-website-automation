import type { Metadata } from "next";
import { Suspense } from "react";
import PaymentReturnClient from "./PaymentReturnClient";

export const metadata: Metadata = {
  title: "Payment status | Airport & City Transfer",
  robots: { index: false, follow: false },
};

export default async function PaymentReturnPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  return (
    <Suspense fallback={null}>
      <PaymentReturnClient locale={locale} />
    </Suspense>
  );
}
