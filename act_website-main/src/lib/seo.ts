import type { Metadata } from "next";
import { publishedLocalesFor, type Locale } from "../../i18n.config";
import { Languages } from "@/constants/enums";

const SITE_URL = "https://airportandcitytransfer.com";

const buildLocalizedUrl = (locale: Locale, path = "") => {
  const normalizedPath = path.replace(/^\/+|\/+$/g, "");
  return normalizedPath
    ? `${SITE_URL}/${locale}/${normalizedPath}`
    : `${SITE_URL}/${locale}`;
};

export const getPublicPageSeo = (
  locale: Locale,
  path = "",
  metadata: Metadata = {}
): Metadata => ({
  ...metadata,
  alternates: {
    ...metadata.alternates,
    canonical: buildLocalizedUrl(locale, path),
    languages: {
      ...Object.fromEntries(publishedLocalesFor(path).map(code => [code, buildLocalizedUrl(code, path)])),
      "x-default": buildLocalizedUrl(Languages.ENGLISH, path),
    },
  },
});

export const privatePageSeo: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};
