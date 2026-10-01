import "server-only";
import { dictionaryLocale, type SupportedLocale } from "../../i18n.config";
import { mergeDictionary } from "./translation-fallback";

const loaders = {
  en: {
    home: () => import("@/dictionaries/en/home.json").then(m => m.default),
    auth: () => import("@/dictionaries/en/auth.json").then(m => m.default),
    complaints: () => import("@/dictionaries/en/complaints.json").then(m => m.default),
    lostProperty: () => import("@/dictionaries/en/lostProperty.json").then(m => m.default),
    tripsPassenger: () => import("@/dictionaries/en/tripsPassenger.json").then(m => m.default),
    driver: () => import("@/dictionaries/en/driver.json").then(m => m.default),
    dashboard: () => import("@/dictionaries/en/dashboard.json").then(m => m.default),
  },
  ar: {
    home: () => import("@/dictionaries/ar/home.json").then(m => m.default),
    auth: () => import("@/dictionaries/ar/auth.json").then(m => m.default),
    complaints: () => import("@/dictionaries/ar/complaints.json").then(m => m.default),
    lostProperty: () => import("@/dictionaries/ar/lostProperty.json").then(m => m.default),
    tripsPassenger: () => import("@/dictionaries/ar/tripsPassenger.json").then(m => m.default),
    driver: () => import("@/dictionaries/ar/driver.json").then(m => m.default),
    dashboard: () => import("@/dictionaries/ar/dashboard.json").then(m => m.default),
  },
};
export default async function getTrans(locale: SupportedLocale, section: string): Promise<any> {
  if (!Object.prototype.hasOwnProperty.call(loaders.en, section)) throw new Error(`Unknown translation section: ${section}`);
  const key = section as keyof typeof loaders.en;
  const english = await loaders.en[key]();
  const language = dictionaryLocale(locale);
  return language === "en" ? english : mergeDictionary(english, await loaders[language][key]());
}
