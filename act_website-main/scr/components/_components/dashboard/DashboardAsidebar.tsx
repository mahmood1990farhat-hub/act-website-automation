"use client";
import { deleteCookie } from "cookies-next";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React, { useState, useEffect } from "react";
import { FaCarAlt, FaTimes, FaUserClock, FaDollarSign, FaMoneyBillWave, FaFile } from "react-icons/fa";
import { FaCarOn, FaMapLocationDot, FaBars } from "react-icons/fa6";
import { MdLuggage, MdMarkunreadMailbox, MdSpaceDashboard, MdTaxiAlert } from "react-icons/md";
import { RiSettingsFill, RiTimerFill } from "react-icons/ri";
import { HiOutlineArrowLeftStartOnRectangle } from "react-icons/hi2";
import { GiCaptainHatProfile } from "react-icons/gi";
import { PiOfficeChairBold } from "react-icons/pi";
import { BiSupport } from "react-icons/bi";
import GlobalModal from "../GlobalModal";
import { Button } from "@/components/ui/button";

export default function DashboardAsidebar({
  trans,
  locale,
  dashboardTrans,
  sidebarOpen,
  setSidebarOpenAction,
}: {
  trans: { name: string; href: string }[];
  locale?: string;
  dashboardTrans?: any;
  sidebarOpen: boolean;
  setSidebarOpenAction: (open: boolean) => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const isRTL = locale === "ar";
  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      const cookiesToClear = [
        "userToken",
        "user_id",
        "account_type",
        "is_admin_verified",
      ];

      cookiesToClear.forEach((cookieName) => deleteCookie(cookieName));
      setShowLogoutConfirm(false);
      
      // Redirect to admin login page
      router.push(`/${locale || "en"}/admin/login`);
      router.refresh();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const icons = [
    <MdSpaceDashboard key="dashboard" />,
    <FaCarOn key="car" />,
    <GiCaptainHatProfile key="captain" />,
    <FaUserClock key="onboarding" />,
    <MdMarkunreadMailbox key="mail" />,
    <FaCarAlt key="car-alt" />,
    <PiOfficeChairBold key="office" />,
    <FaMapLocationDot key="map" />,
    <RiTimerFill key="timer" />,
    <MdLuggage key="luggage" />,
    <BiSupport key="support" />,
    <MdTaxiAlert key="taxi" />,
    <FaDollarSign key="pricing" />,
    <FaMoneyBillWave key="earnings" />,
    <FaFile key="static-files" />,
    <RiSettingsFill key="settings" />,
  ];

  // Close sidebar when clicking outside on mobile
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        sidebarOpen &&
        !target.closest(".sidebar-container") &&
        !target.closest(".sidebar-toggle")
      ) {
        setSidebarOpenAction(false);
      }
    };

    if (sidebarOpen) {
      document.addEventListener("click", handleClickOutside);
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }

    return () => {
      document.removeEventListener("click", handleClickOutside);
      document.body.style.overflow = "unset";
    };
  }, [sidebarOpen, setSidebarOpenAction]);

  return (
    <>
      {/* Mobile Overlay */}
      <div
        className={`fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden transition-opacity duration-300 ${
          sidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={() => setSidebarOpenAction(false)}
      />

      {/* Sidebar */}
      <aside
        className={`sidebar-container fixed md:sticky top-0 h-screen bg-foreground text-white z-50 transition-transform duration-300 ease-in-out overflow-hidden flex flex-col
          ${isRTL ? "right-0 md:left-0" : "left-0"}
          ${sidebarOpen 
            ? "translate-x-0" 
            : isRTL 
              ? "translate-x-full md:translate-x-0" 
              : "-translate-x-full md:translate-x-0"
          }
          w-[280px] sm:!min-w-[300px] md:w-72 lg:w-80 shadow-2xl md:shadow-none
        `}
      >
        {/* Header Section */}
        {/* <div className="py-8 px-6 border-b border-white/10 bg-gradient-to-b from-gray-800/50 to-transparent">
          <h1 className="text-xl font-bold leading-tight text-center text-white mb-2">
            Airport City Group
          </h1>
          <p className="text-sm text-gray-400 text-center">Admin Dashboard</p>
        </div> */}
        <div className="py-8 px-6 border-b border-white/10 bg-gradient-to-b from-gray-800/50 to-transparent">
           <div className="flex items-center gap-4">
            <div className="relative w-12 h-12">
              <Image
                src="/images/driver/logo_in_diver.png"
                alt={dashboardTrans?.logoAlt || "logo"}
                fill
                className="object-contain"
              />
            </div>
            <div>
              <h1 className="text-xl font-bold text-primary">
                Airport & City Transfer
              </h1>
              <p className="text-xs text-gray-400">
                {dashboardTrans?.brandSubtitle || "Admin Dashboard"}
              </p>
            </div>
          </div>
          </div>


        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto on-scrollbar px-4 py-6">
          <ul className="space-y-1.5">
            {trans.map((item, index) => {
              const isActive = pathname === item.href;
              
              // Show selected navigation items only:
              // 0 - Dashboard, 1 - Trips, 2 - Drivers, 3 - Driver Onboarding, 4 - Passengers,
              // 9 - Lost Luggage, 10 - Complaints, 12 - Pricing, 13 - Earnings, 14 - Static Files
              const visibleIndexes = [0, 1, 2, 4, 3, 9, 10, 12, 13, 14];
              if (!visibleIndexes.includes(index)) {
                return null;
              }
              
              /* Commented out navigation items:
              0 - Dashboard (ACTIVE - shown)
              1 - Trips (ACTIVE - shown)
              2 - Drivers (ACTIVE - shown)
              3 - Driver Onboarding (ACTIVE - shown)
              4 - Passengers (ACTIVE - shown)
              5 - Vehicles
              6 - Offices
              7 - Monitor trip
              8 - Pinned trips
              9 - Lost Luggage (ACTIVE - shown)
              10 - Complaints (ACTIVE - shown)
              11 - Trips Complaints
              12 - Pricing (ACTIVE - shown)
              13 - Earnings (ACTIVE - shown)
              14 - Settings
              */
              
              return (
                <li key={index}>
                  <Link
                    href={item.href}
                    className={`group flex items-center gap-4 px-5 py-4 rounded-xl font-medium transition-all duration-200 ${
                      isActive
                        ? "bg-primary text-foreground shadow-lg shadow-primary/20"
                        : "text-white hover:bg-white/10 " +
                          (isRTL ? "hover:-translate-x-1" : "hover:translate-x-1")
                    }`}
                    onClick={() => setSidebarOpenAction(false)}
                  >
                    <span className={`text-2xl transition-transform duration-200 ${
                      isActive ? '' : 'group-hover:scale-110'
                    }`}>
                      {icons[index]}
                    </span>
                    <span className="text-base">{item.name}</span>
                  </Link>
                </li>
              );
            })}
            
            {/* Logout as Navigation Item - Mobile Only */}
            <li className="md:hidden">
              <button
                onClick={() => {
                  setShowLogoutConfirm(true);
                  setSidebarOpenAction(false);
                }}
                className="group w-full flex items-center gap-4 px-5 py-4 rounded-xl font-medium transition-all duration-200 text-red-400 hover:bg-red-500/10 hover:text-red-300"
              >
                <span className="text-2xl transition-transform duration-200 group-hover:scale-110">
                  <HiOutlineArrowLeftStartOnRectangle />
                </span>
                <span className="text-base">{dashboardTrans?.logout || "Logout"}</span>
              </button>
            </li>
          </ul>
        </nav>

        {/* Logout Button - Desktop Only */}
        <div className="hidden md:block px-3 md:px-4 py-4 md:py-5 border-t border-white/10 bg-gradient-to-t from-gray-800/50 to-transparent">
          <button
            className="group w-full flex items-center justify-center gap-2 md:gap-3 px-3 md:px-5 py-2.5 md:py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg border border-red-500/30 hover:border-red-500/50 transition-all duration-200 font-medium text-sm md:text-base"
          onClick={() => setShowLogoutConfirm(true)}
          >
            <HiOutlineArrowLeftStartOnRectangle className="text-lg md:text-xl transition-transform duration-200 group-hover:scale-110 flex-shrink-0" />
            <span className="truncate">{dashboardTrans?.logout || "Logout"}</span>
          </button>
        </div>

        {/* Bottom Accent */}
        <div className="h-1 bg-gradient-to-r from-primary via-accent to-primary" />
      </aside>

      {/* Logout Confirmation Modal */}
      <GlobalModal
        isOpen={showLogoutConfirm}
        onClose={() => setShowLogoutConfirm(false)}
        maxWidth="md"
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 w-full">
            <div className="flex items-center gap-4 pb-4 border-b border-border">
              <div className="p-3 rounded-full bg-red-500/10">
                <HiOutlineArrowLeftStartOnRectangle className="text-2xl text-red-400" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-red-400">
                  {dashboardTrans?.logoutConfirmTitle || "Confirm Logout"}
                </h2>
                <p className="text-sm text-muted mt-1">
                  {dashboardTrans?.logoutConfirmMessage ||
                    "Are you sure you want to logout from the admin dashboard?"}
                </p>
              </div>
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-border">
              <Button
              variant="secondary"
                type="button"
                onClick={() => setShowLogoutConfirm(false)}
              >
                {dashboardTrans?.cancel || "Cancel"}
              </Button>
              <Button
                variant="destructive"
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-sm font-semibold text-white shadow-lg shadow-red-500/30 transition-colors disabled:opacity-50"
              >
                {isLoggingOut
                  ? dashboardTrans?.loggingOut || "Logging out..."
                  : (dashboardTrans?.confirm || "Logout")}
              </Button>
            </div>
        </div>
      </GlobalModal>
    </>
  );
}
