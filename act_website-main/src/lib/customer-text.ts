import fr from "@/dictionaries/fr/customerInterface.json";
import de from "@/dictionaries/de/customerInterface.json";
import es from "@/dictionaries/es/customerInterface.json";
import tr from "@/dictionaries/tr/customerInterface.json";
import zh from "@/dictionaries/zh-CN/customerInterface.json";
const catalogues: Record<string, Record<string, string>> = { fr, de, es, tr, "zh-CN": zh };
/** Display text only; never translate stored IDs, addresses or customer input. */
export function customerText(locale: string, english: string): string {
  return catalogues[locale]?.[english] ?? english;
}
