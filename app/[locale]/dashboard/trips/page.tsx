import { cookies } from "next/headers";
import React from "react";
import { Locale } from "../../../../../i18n.config";
import getTrans from "@/lib/translation";
import TripsDashboard from "@/components/_components/dashboard/TripsDashboard";

// Mark this route as dynamic so Next.js doesn't try to pre-generate static paths for it
export const dynamic = "force-dynamic";

export default async function DashboardTripsPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const locale = (await params).locale;
  const { dashboard } = await getTrans(locale, "dashboard");
  const token = (await cookies()).get("userToken")?.value;

  return (
    <div className="">
      <TripsDashboard locale={locale} token={token} trans={dashboard} />
    </div>
  );
}