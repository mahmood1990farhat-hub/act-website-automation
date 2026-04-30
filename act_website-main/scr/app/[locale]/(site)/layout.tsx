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
      <main
        className="relative overflow-clip bg-cover bg-center text-white min-h-[700px]">
        <Header navbar={navbar} locale={locale} token={token} />
        {children}
      </main>
      <Footer footer={footer} privacyPolicy={policy_and_terms.policy} terms={policy_and_terms.terms} faqs={faqs} locale={locale} />
    </>
  );
}
