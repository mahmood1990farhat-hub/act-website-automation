import React from "react";
import { Locale } from "../../../../../i18n.config";
import getTrans from "@/lib/translation";
import { cookies } from "next/headers";
import DriverOnboardingRequests from "@/components/_components/dashboard/DriverOnboardingRequests";

type TypeProps = {
  params: Promise<{ locale: Locale }>;
};

export default async function DriverOnboardingPage({ params }: TypeProps) {
  const { locale } = await params;
  const { dashboard } = await getTrans(locale, "dashboard");
  const cookieStore = await cookies();
  const token = cookieStore.get("userToken")?.value;

  return (
    <div>
      <DriverOnboardingRequests token={token} locale={locale} trans={{ ...dashboard.driverOnboarding, ...dashboard }} />
    </div>
  );
}


