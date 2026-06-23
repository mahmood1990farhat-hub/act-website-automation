import { headers } from "next/headers";
import { i18n, Locale } from "../../i18n.config";
import ReactQueryProvider from "@/providers/Provider";
import ProviderMap from "@/providers/ProviderMap";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import "./globals.css";
import Script from "next/script";

const getLocaleFromHeaders = async (): Promise<Locale> => {
  const headersList = await headers();
  const rawPath = headersList.get("x-pathname") || headersList.get("x-url") || "";
  const pathname = rawPath.startsWith("http") ? new URL(rawPath).pathname : rawPath;
  const segment = pathname.split("/")[1];

  if (segment && i18n.locales.includes(segment as Locale)) {
    return segment as Locale;
  }

  return i18n.defaultLocale as Locale;
};

export const metadata = {
  title: "ACT",
  description: "Airport & City Transfer",
  verification: {
    google: "-JqU021-FySgKIvmSaumQHIfWj7G5DqRJurNdON7xOc",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocaleFromHeaders();

  return (
    <html
      lang={locale}
      dir={locale === "en" ? "ltr" : "rtl"}
      className="font-sans"
    >
      <head>
        <link rel="icon" type="image/svg+xml" href="/images/logo.svg" />
      </head>
      <body>
        <Script
          src="https://www.googletagmanager.com/gtag/js?id=AW-17641563982"
          strategy="afterInteractive"
        />
        <Script id="google-ads-tag" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'AW-17641563982');
          `}
        </Script>
        <ReactQueryProvider>
          <ProviderMap>{children}</ProviderMap>
          <ToastContainer
            position="top-right"
            autoClose={5000}
            theme="light"
            toastStyle={{
              fontSize: "14px",
              color: "white",
              backgroundColor: "#18181A",
              fontWeight: "bold",
            }}
            toastClassName="custom-toast"
            hideProgressBar
            style={{ zIndex: 10000 }}
          />
        </ReactQueryProvider>
      </body>
    </html>
  );
}

