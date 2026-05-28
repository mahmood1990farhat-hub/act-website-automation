import Footer from "@/components/_components/footer/Footer";
import getTrans from "@/lib/translation";
import { Locale } from "../../../../i18n.config";
import Header from "@/components/_components/header/Header";
import { cookies } from "next/headers";

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const locale = (await params).locale as Locale;
  const { navbar, footer, policy_and_terms, faqs } = await getTrans(locale, 'home');
  const token = (await cookies()).get("userToken")?.value

  return (
    <>
          <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "LocalBusiness",
          name: "Airport & City Transfer",
          url: "https://airportandcitytransfer.com",
          image: "https://airportandcitytransfer.com/images/logo.png",
          description:
            "Airport & City Transfer provides private airport transfers, executive transfers, chauffeur services and city transport across London.",
          areaServed: [
            "London",
            "Heathrow Airport",
            "Gatwick Airport",
            "Stansted Airport",
            "Luton Airport",
            "London City Airport",
          ],
          serviceType: [
            "Airport Transfer",
            "Private Hire Transfer",
            "Executive Airport Transfer",
            "Chauffeur Service",
            "7 Seater Airport Transfer",
          ],
          provider: {
            "@type": "Organization",
            name: "Airport & City Transfer",
            url: "https://airportandcitytransfer.com",
          },
        }),
      }}
    />
      <main
        className="relative overflow-clip bg-cover bg-center text-white min-h-[700px]">
        <Header navbar={navbar} locale={locale} token={token} />
        {children}
      </main>
      <Footer footer={footer} privacyPolicy={policy_and_terms.policy} terms={policy_and_terms.terms} faqs={faqs} locale={locale} />
    </>
  );
}
