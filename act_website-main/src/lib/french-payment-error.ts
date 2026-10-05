// Display-only translations. Never change payment status or retry a payment.
const messages: Record<string, string> = {
  card_declined: "Votre carte a été refusée. Utilisez une autre carte ou contactez votre banque.",
  expired_card: "Votre carte a expiré. Utilisez une autre carte.",
  incorrect_cvc: "Le cryptogramme visuel (CVC) est incorrect.",
  invalid_cvc: "Vérifiez le cryptogramme visuel (CVC).",
  incomplete_cvc: "Saisissez le cryptogramme visuel (CVC).",
  incorrect_number: "Le numéro de carte est incorrect.",
  invalid_number: "Vérifiez le numéro de carte.",
  incomplete_number: "Saisissez le numéro de carte complet.",
  incomplete_expiry: "Saisissez la date d’expiration complète.",
  invalid_expiry_month: "Vérifiez le mois d’expiration.",
  invalid_expiry_year: "Vérifiez l’année d’expiration.",
  payment_intent_authentication_failure: "L’authentification du paiement a échoué. Contactez votre banque si nécessaire.",
};
export function frenchPaymentError(error: { code?: string }) {
  return (error.code && messages[error.code]) || "Le paiement n’a pas pu être confirmé. Vérifiez son état auprès d’ACT avant de réessayer.";
}
