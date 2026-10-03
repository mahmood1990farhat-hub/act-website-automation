import messages from "@/dictionaries/customer-account.json";
type Key = keyof typeof messages.en;
export function accountText(locale: string | undefined, key: Key): string {
  const language = locale && Object.prototype.hasOwnProperty.call(messages, locale) ? locale as keyof typeof messages : "en";
  return messages[language][key];
}
