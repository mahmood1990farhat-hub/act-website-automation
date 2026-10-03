import copy from "../dictionaries/customer-runtime.json";
export type RuntimeKey = keyof typeof copy.en;
export function runtimeText(locale: string, key: RuntimeKey): string {
  return (copy[locale as keyof typeof copy] ?? copy.en)[key];
}
export function customerPaymentError(locale: string, error: { code?: string }): string {
  const code = error.code;
  const allowed = ["card_declined", "expired_card", "incorrect_cvc", "invalid_cvc", "incomplete_cvc", "incorrect_number", "invalid_number", "incomplete_number", "incomplete_expiry", "invalid_expiry_month", "invalid_expiry_year", "payment_intent_authentication_failure"];
  return runtimeText(locale, code && allowed.includes(code) ? code as RuntimeKey : "paymentUnknown");
}
