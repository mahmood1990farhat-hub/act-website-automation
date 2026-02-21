"use client";

import React, { useState, useRef, useEffect } from "react";
import { HiOutlineArrowLeftStartOnRectangle, HiChevronDown, HiOutlineUser } from "react-icons/hi2";
import { deleteCookie, getCookie } from "cookies-next";
import { useRouter } from "next/navigation";
import { Locale } from "../../../../i18n.config";
import { toast } from "react-toastify";
import Link from "next/link";
import GlobalModal from "../GlobalModal";
import { Button } from "@/components/ui/button";

type PassengerAccountMenuProps = {
  locale: Locale;
  trans: {
    logout: string;
    profile?: string;
    profileDescription?: string;
    logoutConfirmTitle?: string;
    logoutConfirmMessage?: string;
    confirm?: string;
    cancel?: string;
    logoutDescription?: string;
    logoutSuccess?: string;
    logoutError?: string;
    loggingOut?: string;
  };
};

export default function PassengerAccountMenu({ locale, trans }: PassengerAccountMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const notifyAuthChange = () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("authStateChanged"));
    }
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      // Clear cookies and logout
      const cookiesToClear = [
        "userToken",
        "user_id",
        "account_type",
        "is_admin_verified",
      ];

      cookiesToClear.forEach((cookieName) => deleteCookie(cookieName));
      setShowLogoutDialog(false);
      setIsOpen(false);
      notifyAuthChange();
      
      // Redirect to home
      router.push(`/${locale}`);
      router.refresh();
      toast.success(trans.logoutSuccess || "Logged out successfully");
    } catch (error) {
      toast.error(trans.logoutError || "Error during logout");
    } finally {
      setIsLoggingOut(false);
    }
  };


  return (
    <>
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="group flex items-center justify-center gap-2 px-5 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg border border-red-500/30 hover:border-red-500/50 transition-all duration-200 font-medium shadow-sm hover:shadow-md"
        >
          <HiOutlineArrowLeftStartOnRectangle className="text-xl transition-transform duration-200 group-hover:scale-110" />
          <span className="text-base">{trans.logout}</span>
          <HiChevronDown className={`text-sm transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-64 bg-foreground border-2 border-primary/30 rounded-xl shadow-2xl z-50 overflow-hidden backdrop-blur-sm">
            <div className="py-2">
              <Link
                href={`/${locale}/profile`}
                onClick={() => setIsOpen(false)}
                className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-primary/10 transition-all duration-200 text-primary group"
              >
                <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                  <HiOutlineUser className="text-xl text-primary" />
                </div>
                <div className="flex flex-col">
                  <span className="font-semibold text-primary">{trans.profile || "Profile"}</span>
                  <span className="text-xs ">
                    {trans.profileDescription || "Manage your account"}
                  </span>
                </div>
              </Link>
              <div className="h-px bg-border/50 mx-2 my-1"></div>
              <button
                onClick={() => {
                  setShowLogoutDialog(true);
                  setIsOpen(false);
                }}
                className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-primary/10 transition-all duration-200 text-primary group"
              >
                <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                  <HiOutlineArrowLeftStartOnRectangle className="text-xl text-primary" />
                </div>
                <div className="flex flex-col">
                  <span className="font-semibold text-primary">{trans.logout}</span>
                  <span className="text-xs ">
                    {trans.logoutDescription || "Sign out of your account"}
                  </span>
                </div>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Logout Confirmation Dialog */}
      <GlobalModal
        isOpen={showLogoutDialog}
        onClose={() => setShowLogoutDialog(false)}
        maxWidth="md"
      >
        <div className="bg-foreground p-6 rounded-xl space-y-6 w-full">
          {/* Header */}
          <div className="flex items-center gap-4 pb-4 border-b border-border">
            <div className="p-3 rounded-full bg-primary/10">
              <HiOutlineArrowLeftStartOnRectangle className="text-2xl text-primary" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-primary">{trans.logoutConfirmTitle || "Confirm Logout"}</h2>
              <p className="text-sm mt-1">{trans.logoutConfirmMessage || "Are you sure you want to logout?"}</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-4 border-t border-border">
            <Button
              variant="ghost"
              onClick={() => setShowLogoutDialog(false)}
              className="border-border"
            >
              {trans.cancel || "Cancel"}
            </Button>
            <Button
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="bg-primary hover:bg-primary/90 text-black font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all disabled:opacity-50"
            >
              {isLoggingOut
                ? trans.loggingOut || "Logging out..."
                : trans.confirm || "Confirm"}
            </Button>
          </div>
        </div>
      </GlobalModal>
    </>
  );
}

