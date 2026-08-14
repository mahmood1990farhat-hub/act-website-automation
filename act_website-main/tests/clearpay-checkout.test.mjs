import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const checkout = readFileSync("src/components/_components/stripe/CheckoutForm.tsx", "utf8");
const paymentReturn = readFileSync("src/app/[locale]/payment-return/PaymentReturnClient.tsx", "utf8");
const conversion = readFileSync("src/components/_components/stripe/booking-conversion.ts", "utf8");

test("checkout uses PaymentElement and confirms the existing PaymentIntent", () => {
  assert.match(checkout, /<PaymentElement/);
  assert.match(checkout, /stripe\.confirmPayment\(/);
  assert.match(checkout, /redirect: "if_required"/);
  assert.doesNotMatch(checkout, /confirmCardPayment|CardNumberElement|CardExpiryElement|CardCvcElement/);
});

test("redirect return verifies the existing PaymentIntent before success", () => {
  assert.match(paymentReturn, /payment_intent_client_secret/);
  assert.match(paymentReturn, /stripe\.retrievePaymentIntent\(clientSecret\)/);
  assert.match(paymentReturn, /paymentIntent\.status === "succeeded"/);
  assert.doesNotMatch(paymentReturn, /confirmPayment|PaymentIntent\.create|initiate-payment/);
});

test("Google Ads conversion remains tied to the successful PaymentIntent ID", () => {
  assert.match(conversion, /transaction_id: transactionId/);
  assert.match(conversion, /AW-17641563982\/0LprCMbR8sQcEM7Ok9xB/);
  assert.match(paymentReturn, /fireBookingCompletedConversion\(\s*paymentIntent\.id/);
});
