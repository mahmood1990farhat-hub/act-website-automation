import Asidebar from "@/components/_components/driver/Asidebar";
import React from "react";
import { Locale } from "../../../../i18n.config";
import getTrans from "@/lib/translation";
import DashboardAsidebar from "@/components/_components/dashboard/DashboardAsidebar";
import DashboardNavbar from "@/components/_components/dashboard/DashboardNavbar";
import DashboardLayoutClient from "@/components/_components/dashboard/DashboardLayoutClient";

export default async function LayoutDashboard({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const localeTyped = locale as Locale;
  const { aside, dashboard } = await getTrans(localeTyped, "dashboard");
  const { navbar } = await getTrans(localeTyped, "home");

  return (
    <DashboardLayoutClient
      locale={localeTyped}
      aside={aside}
      dashboard={dashboard}
      navbar={navbar}
    >
      {children}
    </DashboardLayoutClient>
  );
}
