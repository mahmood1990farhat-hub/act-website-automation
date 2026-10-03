const text = {
  en: ["Choose language", "Your booking details were kept. Review the route and continue to refresh the quote.", "Please finish or resolve the current payment before changing language.", "We could not keep your booking details while changing language. Your current booking has been left open."],
  ar: ["اختر اللغة", "تم الاحتفاظ ببيانات حجزك. راجع المسار وتابع لتحديث السعر.", "يرجى إكمال عملية الدفع الحالية أو التحقق من نتيجتها قبل تغيير اللغة.", "تعذّر الاحتفاظ ببيانات الحجز عند تغيير اللغة. بقي حجزك الحالي مفتوحًا."],
  fr: ["Choisir une langue", "Vos informations de réservation ont été conservées. Vérifiez le trajet et continuez pour actualiser le tarif.", "Terminez le paiement en cours ou vérifiez son résultat avant de changer de langue.", "Impossible de conserver vos informations lors du changement de langue. Votre réservation actuelle reste ouverte."],
  de: ["Sprache wählen", "Ihre Buchungsdaten wurden übernommen. Prüfen Sie die Route und fahren Sie fort, um den Preis zu aktualisieren.", "Schließen Sie die aktuelle Zahlung ab oder klären Sie deren Ergebnis, bevor Sie die Sprache ändern.", "Ihre Buchungsdaten konnten beim Sprachwechsel nicht übernommen werden. Ihre aktuelle Buchung bleibt geöffnet."],
  es: ["Elegir idioma", "Se han conservado los datos de tu reserva. Revisa la ruta y continúa para actualizar el precio.", "Completa el pago actual o comprueba su resultado antes de cambiar de idioma.", "No se han podido conservar tus datos al cambiar de idioma. Tu reserva actual sigue abierta."],
  tr: ["Dil seçin", "Rezervasyon bilgileriniz korundu. Rotayı kontrol edip güncel fiyatı almak için devam edin.", "Dili değiştirmeden önce mevcut ödemeyi tamamlayın veya sonucunu kontrol edin.", "Dil değiştirilirken rezervasyon bilgileriniz korunamadı. Mevcut rezervasyonunuz açık bırakıldı."],
  "zh-CN": ["选择语言", "您的预订信息已保留。请检查路线并继续，以获取最新报价。", "请先完成当前付款或确认付款结果，再切换语言。", "切换语言时无法保留预订信息。当前预订页面仍保持打开。"],
};
export function languageSwitchText(locale: string, key: "choose" | "restored" | "payment" | "failed") {
  const index = {choose:0, restored:1, payment:2, failed:3}[key];
  return (Object.prototype.hasOwnProperty.call(text, locale) ? text[locale as keyof typeof text] : text.en)[index];
}
