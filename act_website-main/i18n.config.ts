import { Languages } from "./src/constants/enums";
export type Locale = Languages.ARABIC | Languages.ENGLISH;
export type languageType = Locale;
export type SupportedLocale = Locale | "zh-CN" | "tr" | "es" | "fr" | "de";
export const localeRegistry: Record<SupportedLocale, { label: string; direction: "ltr" | "rtl"; enabled: boolean }> = {
  en: { label: "English", direction: "ltr", enabled: true },
  ar: { label: "العربية", direction: "rtl", enabled: true },
  "zh-CN": { label: "简体中文", direction: "ltr", enabled: false },
  tr: { label: "Türkçe", direction: "ltr", enabled: false },
  es: { label: "Español", direction: "ltr", enabled: false },
  fr: { label: "Français", direction: "ltr", enabled: false },
  de: { label: "Deutsch", direction: "ltr", enabled: false },
};
export const isSupportedLocale = (value: string): value is SupportedLocale =>
  Object.prototype.hasOwnProperty.call(localeRegistry, value);
// Fail closed: a flag alone cannot publish a locale without its dictionary contract.
export const isEnabledLocale = (value: string): value is Locale =>
  (value === Languages.ENGLISH || value === Languages.ARABIC) && localeRegistry[value].enabled;
export const enabledLocales = (Object.keys(localeRegistry) as SupportedLocale[]).filter(isEnabledLocale);
export const i18n = { defaultLocale: Languages.ARABIC, locales: enabledLocales };
export const directionFor = (locale: string) => locale === "ar" ? "rtl" : "ltr";
export const dictionaryLocale = (locale: string): Locale => locale === "ar" ? Languages.ARABIC : Languages.ENGLISH;
export const localeFromPath = (path: string): Locale | undefined => {
  const segment = path.split(/[?#]/, 1)[0].split("/")[1];
  return isEnabledLocale(segment || "") ? segment as Locale : undefined;
};
export function localizedPath(path: string, locale: Locale): string {
  if (!path.startsWith("/") || path.startsWith("//")) return path;
  const match = path.match(/^\/([^/?#]+)(.*)$/);
  return match && isSupportedLocale(match[1]) ? `/${locale}${match[2]}` : `/${locale}${path === "/" ? "" : path}`;
}
export function localizedVehicleValue(
  vehicle: { name_en?: string; name_ar?: string; desc_en?: string; desc_ar?: string },
  field: "name" | "desc", locale: string,
): string {
  return vehicle[`${field}_${dictionaryLocale(locale)}`] || vehicle[`${field}_en`] || vehicle[`${field}_ar`] || "";
}
export const publicRoutes = ["", "about-us", "download-app", "complaints", "lost-property",
  "heathrow-airport-transfer", "gatwick-airport-transfer", "stansted-airport-transfer",
  "luton-airport-transfer", "london-city-airport-transfer"];
export const publishedLocalesFor = (path: string): Locale[] =>
  publicRoutes.includes(path.replace(/^\/+|\/+$/g, "")) ? enabledLocales : [];
