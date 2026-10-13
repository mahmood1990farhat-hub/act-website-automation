import DriverPasswordSetup from "@/components/_components/auth/captain/DriverPasswordSetup";
import { Locale } from "../../../../../i18n.config";
import { privatePageSeo } from "@/lib/seo";

export const metadata = privatePageSeo;

export default async function DriverPasswordSetupPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  return <DriverPasswordSetup locale={locale} />;
}
