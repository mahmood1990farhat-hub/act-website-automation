
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
  return getPublicPageSeo(locale);
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
