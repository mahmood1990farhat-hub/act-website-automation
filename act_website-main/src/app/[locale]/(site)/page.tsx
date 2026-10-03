
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
  const copy = await getTrans(locale, "home");
  return getPublicPageSeo(locale, "", {title: copy.home.Book_Taxi.title + " | Airport & City Transfer", description: copy.home.Book_Taxi.subtitle});
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

