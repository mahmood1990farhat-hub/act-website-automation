import { cookies } from "next/headers";
import React from "react";
import { Locale } from "../../../../../i18n.config";
import getTrans from "@/lib/translation";
import LostLuggageDashboard from "@/components/_components/dashboard/LostLuggageDashboard";

export default async function DashboardLostluggagePage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const locale = (await params).locale;
  const lostPropertyTrans = await getTrans(locale, "lostProperty");
  const token = (await cookies()).get("userToken")?.value;

  return (
    <div className="py-4">
      <LostLuggageDashboard trans={lostPropertyTrans} token={token} locale={locale} />
    </div>
  );
}