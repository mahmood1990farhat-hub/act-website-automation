"use client";

import { loadStripe } from "@stripe/stripe-js";
import { CheckCircle, CircleAlert, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { fireBookingCompletedConversion } from "@/components/_components/stripe/booking-conversion";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

type ReturnState = "checking" | "succeeded" | "processing" | "failed";

export default function PaymentReturnClient({ locale }: { locale: string }) {
  const searchParams = useSearchParams();
  const [state, setState] = useState<ReturnState>("checking");

  useEffect(() => {
    let active = true;
    const verifyPayment = async () => {
      const clientSecret = searchParams.get("payment_intent_client_secret");
      const stripe = await stripePromise;
      if (!stripe || !clientSecret) {
        if (active) setState("failed");
        return;
      }

      const { paymentIntent, error } = await stripe.retrievePaymentIntent(clientSecret);
      if (!active) return;
      if (error || !paymentIntent) {
        setState("failed");
      } else if (paymentIntent.status === "succeeded") {
        await fireBookingCompletedConversion(
          paymentIntent.id,
          paymentIntent.amount / 100,
        );
        if (active) setState("succeeded");
      } else if (paymentIntent.status === "processing") {
        setState("processing");
      } else {
        setState("failed");
      }
    };
    void verifyPayment();
    return () => { active = false; };
  }, [searchParams]);

  const isArabic = locale === "ar";
  const content = {
    checking: ["Checking your payment", "جارٍ التحقق من عملية الدفع"],
    succeeded: ["Booking confirmed", "تم تأكيد الحجز"],
    processing: ["Payment is processing", "عملية الدفع قيد المعالجة"],
    failed: ["Payment was not completed", "لم تكتمل عملية الدفع"],
  }[state][isArabic ? 1 : 0];
  const description = state === "succeeded"
    ? (isArabic ? "تم استلام دفعتك. سيصلك تأكيد الحجز عبر البريد الإلكتروني." : "Your payment was received. Your booking confirmation will be sent by email.")
    : state === "processing"
      ? (isArabic ? "سنرسل تأكيد الحجز بعد أن تؤكد Stripe عملية الدفع." : "We will send your booking confirmation when Stripe confirms the payment.")
      : state === "checking"
        ? (isArabic ? "يرجى الانتظار وعدم إغلاق هذه الصفحة." : "Please wait and do not close this page.")
        : (isArabic ? "يمكنك العودة إلى صفحة الحجز والمحاولة مرة أخرى." : "You can return to the booking page and try again.");

  const Icon = state === "succeeded" ? CheckCircle : state === "failed" ? CircleAlert : LoaderCircle;
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#18181a] px-4 text-white">
      <section className="w-full max-w-lg border border-white/15 bg-[#242426] p-8 text-center shadow-2xl">
        <Icon className={`mx-auto mb-5 h-12 w-12 text-[#ffd100] ${state === "checking" ? "animate-spin" : ""}`} />
        <h1 className="text-2xl font-semibold">{content}</h1>
        <p className="mt-3 text-sm leading-6 text-white/75">{description}</p>
        {state !== "checking" && (
          <Link href={`/${locale}`} className="mt-7 inline-flex min-h-11 items-center bg-[#ffd100] px-6 font-semibold text-black">
            {isArabic ? "العودة إلى الصفحة الرئيسية" : "Return to homepage"}
          </Link>
        )}
      </section>
    </main>
  );
}
