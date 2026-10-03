import en from "react-phone-number-input/locale/en.json";
import ar from "react-phone-number-input/locale/ar.json";
import fr from "react-phone-number-input/locale/fr.json";
import de from "react-phone-number-input/locale/de.json";
import es from "react-phone-number-input/locale/es.json";
import tr from "react-phone-number-input/locale/tr.json";
import zh from "react-phone-number-input/locale/zh.json";

const labels = { en, ar, fr, de, es, tr, "zh-CN": zh };
/** Localize country names only; phone numbers remain in canonical E.164 format. */
export function customerPhoneLabels(locale: string) {
  return Object.prototype.hasOwnProperty.call(labels, locale)
    ? labels[locale as keyof typeof labels] : labels.en;
}
