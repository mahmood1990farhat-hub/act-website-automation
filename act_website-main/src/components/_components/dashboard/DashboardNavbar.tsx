"use client";

import React from "react";
import { Locale } from "../../../../i18n.config";
import { TbWorld } from "react-icons/tb";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { FaBars } from "react-icons/fa6";
import { FaTimes } from "react-icons/fa";

type DashboardNavbarProps = {
  locale: Locale;
  language: {
    English: string;
    Arabic: string;
  };
  dashboardTrans?: {
    adminLabel?: string;
    defaultTitle?: string;
    toggleSidebar?: string;
    languageShortEn?: string;
    languageShortAr?: string;
  };
  menuItems: {
    name: string;
    href: string;
  }[];
  sidebarOpen: boolean;
  setSidebarOpenAction: (open: boolean) => void;
};

export default function DashboardNavbar({
  locale,
  language,
  dashboardTrans,
  menuItems,
  sidebarOpen,
  setSidebarOpenAction,
}: DashboardNavbarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleLanguageSwitch = () => {
    const newLocale = locale === "en" ? "ar" : "en";
    const newPathname = pathname.replace(`/${locale}`, `/${newLocale}`);
    router.push(newPathname);
  };

  const normalizedPath = pathname.replace(/\/$/, "");

  const activeItem = menuItems.find((item) => {
    const normalizedHref = item.href.replace(/\/$/, "");
    if (normalizedPath === normalizedHref) return true;
    return normalizedPath.startsWith(`${normalizedHref}/`);
  });

  const defaultTitle =
    menuItems[0]?.name ||
    dashboardTrans?.defaultTitle ||
    (locale === "ar" ? "لوحة التحكم" : "Dashboard");
  const pageTitle = activeItem?.name || defaultTitle;
  const adminLabel =
    dashboardTrans?.adminLabel || (locale === "ar" ? "لوحة تحكم المشرف" : "Admin Dashboard");

  return (
    <div
      className={`sticky top-0 z-50 bg-gradient-to-r from-foreground via-gray-900 to-foreground border-b-2 border-primary/30 shadow-lg transition-transform duration-300 ${
        sidebarOpen ? "max-md:-translate-y-full" : "max-md:translate-y-0"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 md:px-6 py-3 md:py-4">
        <div className="flex items-center justify-between">
          {/* Left Side - Menu Button + Heading (Mobile) / Language Switcher (Desktop) */}
          <div className="flex items-center gap-3 md:gap-4">
            {/* Menu Button - Mobile Only (Left Side) */}
            <button
              onClick={() => setSidebarOpenAction(!sidebarOpen)}
              className="md:hidden p-2 hover:bg-white/10 rounded-lg transition-colors text-white"
              aria-label={dashboardTrans?.toggleSidebar || "Toggle sidebar"}
            >
              {sidebarOpen ? (
                <FaTimes className="text-xl" />
              ) : (
                <FaBars className="text-xl" />
              )}
            </button>
            
            {/* Heading - Mobile Only (with menu button) */}
            <div
              className={`md:hidden flex flex-col ${
                locale === "ar" ? "items-end text-right" : "text-left"
              }`}
            >
              <h1 className="text-base md:text-lg lg:text-xl font-bold text-white">
                {pageTitle}
              </h1>
            </div>
            
            {/* Language Toggle Button - Desktop Only (Left Side) */}
            <button
              onClick={handleLanguageSwitch}
              className="hidden md:flex group items-center gap-1.5 md:gap-2 px-3 md:px-4 py-2 md:py-2.5 bg-primary/10 hover:bg-primary/20 text-primary hover:text-primary/80 rounded-lg border border-primary/30 hover:border-primary/50 transition-all duration-200 font-medium"
            >
              <TbWorld className="text-base md:text-lg transition-transform duration-200 group-hover:scale-110" />
              <span className="text-xs md:text-sm">
                {locale === "en"
                  ? dashboardTrans?.languageShortAr || "AR"
                  : dashboardTrans?.languageShortEn || "EN"}
              </span>
            </button>
          </div>

          {/* Right Side - Language Switcher (Mobile) / Logo and Brand (Desktop) */}
          <div className="flex items-center gap-3 md:gap-4">
            {/* Language Toggle Button - Mobile Only (Right Side) */}
            <button
              onClick={handleLanguageSwitch}
              className="md:hidden group flex items-center gap-1.5 md:gap-2 px-3 md:px-4 py-2 md:py-2.5 bg-primary/10 hover:bg-primary/20 text-primary hover:text-primary/80 rounded-lg border border-primary/30 hover:border-primary/50 transition-all duration-200 font-medium"
            >
              <TbWorld className="text-base md:text-lg transition-transform duration-200 group-hover:scale-110" />
              <span className="text-xs md:text-sm">
                {locale === "en"
                  ? dashboardTrans?.languageShortAr || "AR"
                  : dashboardTrans?.languageShortEn || "EN"}
              </span>
            </button>

            <Link href="/" className="hidden md:block">
              <div className="relative w-12 h-12">
                <Image
                  src="/images/driver/logo_in_diver.png"
                  alt="logo"
                  fill
                  className="object-contain"
                />
              </div>
            </Link>
            <div
              className={`hidden md:flex flex-col ${
                locale === "ar" ? "items-end text-right" : "text-left"
              }`}
            >
              <span className="text-xs uppercase tracking-[0.3em] text-primary/70 font-semibold">
                {adminLabel}
              </span>
              <h1 className="text-base md:text-lg lg:text-xl font-bold text-white md:mt-1">
                {pageTitle}
              </h1>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

