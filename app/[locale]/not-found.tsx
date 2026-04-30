import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Home, AlertCircle } from "lucide-react";
import { headers } from "next/headers";
import { i18n, Locale } from "../../../i18n.config";
import getTrans from "@/lib/translation";
import GoBackButton from "./_components/GoBackButton";

const extractLocaleFromPath = (rawPath: string): Locale | null => {
  if (!rawPath) return null;
  const pathname = rawPath.startsWith("http") ? new URL(rawPath).pathname : rawPath;
  const segment = pathname.split("/")[1];
  if (segment && i18n.locales.includes(segment as Locale)) {
    return segment as Locale;
  }
  return null;
};

const getLocaleFromHeaders = async (): Promise<Locale> => {
  const headersList = await headers();
  const candidates = [
    headersList.get("x-pathname"),
    headersList.get("x-url"),
    headersList.get("next-url"),
    headersList.get("referer"),
  ].filter(Boolean) as string[];

  for (const candidate of candidates) {
    const locale = extractLocaleFromPath(candidate);
    if (locale) return locale;
  }

  return i18n.defaultLocale as Locale;
};

export default async function NotFound({
  params,
}: {
  params?: Promise<{ locale?: Locale }>;
}) {
  const resolvedParams = params ? await params : undefined;
  const locale = resolvedParams?.locale || (await getLocaleFromHeaders());
  const isRTL = locale === "ar";
  const { errorPage } = await getTrans(locale, "home");

  return (
    <div
      dir={isRTL ? "rtl" : "ltr"}
      className={`min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 px-4 ${
        isRTL ? "rtl" : "ltr"
      }`}
    >
      <div className="max-w-2xl w-full text-center space-y-8">
        <div className="flex justify-center">
          <div className="relative">
            <div className="absolute inset-0 bg-primary/20 rounded-full blur-3xl animate-pulse"></div>
            <div className="relative bg-primary/10 rounded-full p-8 border-4 border-primary/30">
              <AlertCircle className="w-24 h-24 text-primary" />
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h1 className="text-6xl md:text-8xl font-bold text-primary">
            {errorPage?.code || "404"}
          </h1>
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white">
            {errorPage?.title || "Page Not Found"}
          </h2>
          <p className="text-lg md:text-xl text-gray-600 dark:text-gray-300 max-w-md mx-auto">
            {errorPage?.description ||
              "Sorry, we couldn't find the page you're looking for. The page might have been moved, deleted, or doesn't exist."}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link href={`/${locale}`}>
            <Button
              size="lg"
              className="w-full sm:w-auto px-8 py-6 text-lg font-semibold bg-primary hover:bg-primary/90 text-white shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer"
            >
              <Home className="w-5 h-5 mr-2" />
              {errorPage?.goHome || "Go Home"}
            </Button>
          </Link>
          <GoBackButton
            locale={locale}
            isRTL={isRTL}
            label={errorPage?.goBack || "Go Back"}
          />
        </div>

        <div className="pt-8 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {errorPage?.helpText ||
              "If you believe this is an error, please contact our support team."}
          </p>
        </div>
      </div>
    </div>
  );
}
