// Preserve translated values/arrays; fill missing object keys from English.
export function mergeDictionary(base: any, translated: any): any {
  if (translated === undefined || translated === null) return base;
  if (Array.isArray(base) || typeof base !== "object" || base === null) return translated;
  if (typeof translated !== "object" || Array.isArray(translated)) return base;
  return Object.fromEntries([...new Set([...Object.keys(base), ...Object.keys(translated)])]
    .map(key => [key, mergeDictionary(base[key], translated[key])]));
}
export function missingTranslationKeys(base: any, translated: any, prefix = ""): string[] {
  if (translated === undefined || translated === null) return [prefix];
  if (base && typeof base === "object" && !Array.isArray(base)) {
    return Object.keys(base).flatMap(key => missingTranslationKeys(base[key], translated?.[key], prefix ? `${prefix}.${key}` : key));
  }
  return [];
}
