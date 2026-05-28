import type { MetadataRoute } from "next";

const baseUrl = "https://airportandcitytransfer.com";

const locales = ["en", "ar"];

const routes = [
  { path: "", priority: 1.0 },
  { path: "about-us", priority: 0.7 },
  { path: "download-app", priority: 0.7 },
  { path: "complaints", priority: 0.7 },
  { path: "lost-property", priority: 0.7 },
  { path: "heathrow-airport-transfer", priority: 0.9 },
  { path: "gatwick-airport-transfer", priority: 0.9 },
  { path: "stansted-airport-transfer", priority: 0.9 },
  { path: "luton-airport-transfer", priority: 0.9 },
  { path: "london-city-airport-transfer", priority: 0.9 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();

  return locales.flatMap((locale) =>
    routes.map((route) => ({
      url: route.path
        ? `${baseUrl}/${locale}/${route.path}`
        : `${baseUrl}/${locale}`,
      lastModified,
      changeFrequency: "weekly",
      priority: route.priority,
    }))
  );
}
