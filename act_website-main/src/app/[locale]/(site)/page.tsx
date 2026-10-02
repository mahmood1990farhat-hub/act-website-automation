
import { Locale } from "../../../../i18n.config";
import getTrans from "@/lib/translation";
import BookTaxi from "@/components/_components/bookTaxi";
import HomeUI from "@/components/_components/HomeInfo";
import { getPublicPageSeo } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  return getPublicPageSeo(locale, "", locale === "fr" ? { title: "Transferts aéroport à Londres | Airport & City Transfer", description: "Réservez votre transfert privé entre les aéroports et Londres avec Airport & City Transfer. Découvrez nos services et obtenez un tarif." } : locale === "ar" ? {
    title: "خدمات النقل من وإلى مطارات لندن | Airport & City Transfer",
    description:
      "احجز خدمات النقل الخاص من وإلى المطارات وداخل لندن مع Airport & City Transfer. تعرّف على خدماتنا واحصل على عرض سعر لرحلتك.",
  } : {
    title: "London Airport Transfers | Airport & City Transfer",
    description:
      "Book private airport and city transfers across London with Airport & City Transfer. Explore airport services and get a quote for your journey.",
  });
}

export default async function Home({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const locale = (await params).locale;
  const { home, policy_and_terms, about_us } = await getTrans(locale, 'home')
  const auth = await getTrans(locale, 'auth')

  return (
    <div className="w-full">
      <BookTaxi home={home} policy_and_terms={policy_and_terms} locale={locale} auth={auth} />
      <HomeUI booking_data={about_us} locale={locale} />
    </div>
  );
}

