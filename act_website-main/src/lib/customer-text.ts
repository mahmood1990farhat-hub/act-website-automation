import french from "@/dictionaries/fr/customerInterface.json";
/** Translate display text only; never apply to stored IDs, addresses or API values. */
export function customerText(locale: string, english: string): string {
  return locale === "fr" ? (french as Record<string, string>)[english] || english : english;
}
