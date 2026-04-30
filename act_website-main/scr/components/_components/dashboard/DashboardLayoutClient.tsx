"use client";

import React, { useState } from "react";
import { Locale } from "../../../../i18n.config";
import DashboardAsidebar from "./DashboardAsidebar";
import DashboardNavbar from "./DashboardNavbar";

type DashboardLayoutClientProps = {
  children: React.ReactNode;
  locale: Locale;
  aside: { name: string; href: string }[];
  dashboard: any;
  navbar: any;
};

export default function DashboardLayoutClient({
  children,
  locale,
  aside,
  dashboard,
  navbar,
}: DashboardLayoutClientProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div
      className="flex min-h-screen bg-gray-100"
      dir={locale === "ar" ? "rtl" : "ltr"}
    >
        <DashboardAsidebar
        trans={aside}
        locale={locale}
        dashboardTrans={dashboard}
        sidebarOpen={sidebarOpen}
        setSidebarOpenAction={setSidebarOpen}
      />

      <div className="flex-1 flex flex-col">
        {/* Top Navbar */}
        <DashboardNavbar
          locale={locale}
          language={navbar.languages}
          dashboardTrans={dashboard}
          menuItems={aside}
          sidebarOpen={sidebarOpen}
          setSidebarOpenAction={setSidebarOpen}
        />

        {/* Content Area */}
        <main className="flex-1 max-md:pt-[60px] md:pt-4 xl:pt-3 px-3 xl:px-4 xl:py-4 h-screen overflow-y-auto on-scrollbar">
          <div className="max-w-7xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}

