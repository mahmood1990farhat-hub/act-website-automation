const assert=require("node:assert/strict"),fs=require("node:fs");
const checkout=fs.readFileSync("src/components/_components/stripe/CheckoutForm.tsx","utf8");

for(const expected of [
  '"/api/payments/booking-status/?"',
  'body?.status === "confirmed"',
  'setPaymentCaptured(true)',
  'runtimeText(locale, "bookingFinalising")',
  'runtimeText(locale, "bookingFinalisingDelayed")',
  'disabled={loading || paymentCaptured}',
  'disabled={!isFormValid || loading || paymentCaptured}',
]) assert.ok(checkout.includes(expected),"missing payment fulfillment safety: "+expected);

const confirmAt=checkout.indexOf('body?.status === "confirmed"');
const conversionAt=checkout.indexOf("await fireBookingCompletedEvents(result.paymentIntent.id)");
assert.ok(confirmAt >= 0 && conversionAt > confirmAt,"booking conversion must follow persisted booking confirmation");
assert.ok(!checkout.includes('nextStep();\n    }\n\n    } catch'),"must not immediately confirm UI on Stripe success alone");

console.log("PASS Stripe success waits for persisted ACT booking and blocks repeat payment");
