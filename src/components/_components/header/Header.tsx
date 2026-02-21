"use client";
import React, { useEffect, useState } from "react";
import SelectLanguage from "../header/SelectLanguage";
import { Locale } from "../../../../i18n.config";
import { IoMenu, IoClose } from "react-icons/io5";
import Link from "next/link";
import Image from "next/image";
import { deleteCookie, getCookie } from "cookies-next";
import { usePathname, useRouter } from "next/navigation";
import { HiOutlineArrowLeftStartOnRectangle } from "react-icons/hi2";
import { TbWorld } from "react-icons/tb";
 import PassengerAccountMenu from "./PassengerAccountMenu";

type tpyeProps = {
  navbar: {
    navLinks: {
      name: string;
      url: string;
      protected?: boolean;
    }[];
    languages: {
      English: string;
      Arabic: string;
    };
    menuToggle?: string;
   auth: {
    login: string;
    logout: string;
    profile?: string;
    profileDescription?: string;
    deleteAccount?: string;
    logoutConfirmTitle?: string;
    logoutConfirmMessage?: string;
    deleteAccountConfirmTitle?: string;
    deleteAccountConfirmMessage?: string;
    passwordLabel?: string;
    passwordRequired?: string;
    confirm?: string;
    cancel?: string;
    logoutDescription?: string;
    logoutSuccess?: string;
    logoutError?: string;
    loggingOut?: string;
   }
  };
  locale: Locale;
  token?:string
};

export default function Header({ navbar, locale ,token }: tpyeProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [authState, setAuthState] = useState(() => ({
    token: token ?? (getCookie("userToken") as string | undefined),
    accountType: getCookie("account_type") as string | undefined,
  }));
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const updateAuthState = () => {
      setAuthState({
        token: (getCookie("userToken") as string | undefined) || undefined,
        accountType: (getCookie("account_type") as string | undefined) || undefined,
      });
    };

    updateAuthState();
    window.addEventListener("authStateChanged", updateAuthState);
    window.addEventListener("focus", updateAuthState);
    document.addEventListener("visibilitychange", updateAuthState);

    return () => {
      window.removeEventListener("authStateChanged", updateAuthState);
      window.removeEventListener("focus", updateAuthState);
      document.removeEventListener("visibilitychange", updateAuthState);
    };
  }, []);

  // Check if user is a driver
  const isDriver = authState.accountType === "normal_driver";
  const isLoggedIn = Boolean(authState.token) && !isDriver;
  
  // Filter navigation links based on login status and account type
  const filteredNavLinks = navbar.navLinks.filter(link => {
    // Logged-in passengers (non-drivers) hide some marketing links
    if (isLoggedIn && authState.accountType === "passenger") {
      const hideLinks = ["Services", "خدمات", "About us", "من نحن", "Contact us", "تواصل معنا","Private tour", "جولات خاصة", "Coach", "حافلة", "Delivery", "توصيل", "Home Removal", "نقل منزلي"];
      return !hideLinks.includes(link.name);
    }
    // Drivers and guests only see non-protected links
    if (!isLoggedIn && link.protected) {
      return false;
    }
    return true;
  });

  const handleLanguageSwitch = () => {
    const newLocale = locale === "en" ? "ar" : "en";
    const newPathname = pathname.replace(`/${locale}`, `/${newLocale}`);
    router.push(newPathname);
  };
  const toggleMenu = () => {
    setIsMenuOpen((prev) => !prev);
  };

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
      setIsMenuOpen(false);
      setAuthState({ token: undefined, accountType: undefined });
      window.dispatchEvent(new Event("authStateChanged"));
      
      // Redirect to home
      router.push(`/${locale}`);
      router.refresh();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleLoginClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    // Check if we're already on the auth page
    if (pathname.includes('/auth')) {
      e.preventDefault();
      // Dispatch custom event to reset auth tab
      window.dispatchEvent(new CustomEvent('resetAuthTab', { detail: { step: 1 } }));
      // Scroll to top
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Normalize URL to use current locale
  const normalizeUrl = (url: string) => {
    // If URL is just "/en" or "/ar", replace with current locale
    if (url === "/en" || url === "/ar") {
      return `/${locale}`;
    }
    // Replace any locale prefix (/en or /ar) with current locale
    return url.replace(/^\/(en|ar)/, `/${locale}`);
  };

  return (
    <div className="relative" dir={locale === "ar" ? "rtl" : "ltr"}>
      <div className="hidden md:flex items-center bg-black justify-between px-14  gap-10 py-5">
        <nav className="" role="navigation">
          <ul
            className={`flex  items-center justify-center text-primary lg:text-lg ${
              locale === "ar" ? "lg:gap-10 md:gap-5" : "md:gap-5 "
            }`}
          >
            {filteredNavLinks.slice(0, 10).map((item) => {
              const normalizedUrl = normalizeUrl(item.url);
              if (item.protected) {
                if (isLoggedIn) {
                  return (
                    <li
                      key={item.name}
                      className={`${
                        normalizedUrl === pathname ? "border-b-2 border-primary" : ""
                      } cursor-pointer`}
                    >
                      {normalizedUrl === "about-us" ? (
                        <a>{item.name}</a>
                      ) : (
                        <Link href={normalizedUrl}>{item.name}</Link>
                      )}
                    </li>
                  );
                }
                return null;
              }
              return (
                <li
                  key={item.name}
                  className={`${
                    normalizedUrl === pathname ? "border-b-2 border-primary" : ""
                  } cursor-pointer`}
                >
                  {normalizedUrl === "about-us" ? (
                    <a>{item.name}</a>
                  ) : (
                    <Link href={normalizedUrl}>{item.name}</Link>
                  )}
                </li>
              );
            })}
            {!isLoggedIn && (
              <Link
                href={`/${locale}/auth`}
                onClick={handleLoginClick}
                className="group flex items-center justify-center gap-3 px-5 py-2 bg-primary/10 hover:bg-primary/20 text-primary hover:text-primary/80 rounded-lg border border-primary/30 hover:border-primary/50 transition-all duration-200 font-medium"
              >
                {navbar?.auth?.login}
              </Link>
            )}
          </ul>
        </nav>
        <div className="flex items-center gap-6">
          {/* <div className="w-fit">
            <SelectLanguage locale={locale} language={navbar.languages} />
          </div> */}

          <button
              onClick={handleLanguageSwitch}
              className="group flex items-center gap-2 px-4 py-2.5 bg-primary/10 hover:bg-primary/20 text-primary hover:text-primary/80 rounded-lg border border-primary/30 hover:border-primary/50 transition-all duration-200 font-medium"
            >
              <TbWorld className="text-lg transition-transform duration-200 group-hover:scale-110" />
              <span className="text-sm">
                {locale === "en" ? navbar.languages?.Arabic || "AR" : navbar.languages?.English || "EN"}
              </span>
            </button>


         {isLoggedIn && authState.accountType === "passenger" ? (
            <PassengerAccountMenu
              locale={locale}
              trans={{
                logout: navbar?.auth?.logout || "Logout",
                profile: navbar?.auth?.profile || "Profile",
                profileDescription: navbar?.auth?.profileDescription,
                logoutConfirmTitle: navbar?.auth?.logoutConfirmTitle || "Confirm Logout",
                logoutConfirmMessage: navbar?.auth?.logoutConfirmMessage || "Are you sure you want to logout?",
                confirm: navbar?.auth?.confirm || "Confirm",
                cancel: navbar?.auth?.cancel || "Cancel",
                logoutDescription: navbar?.auth?.logoutDescription,
                logoutSuccess: navbar?.auth?.logoutSuccess,
                logoutError: navbar?.auth?.logoutError,
                loggingOut: navbar?.auth?.loggingOut,
              }}
            />
          ) : isLoggedIn ? (
            <button
              className="group w-full flex items-center justify-center gap-3 px-5 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg border border-red-500/30 hover:border-red-500/50 transition-all duration-200 font-medium disabled:opacity-50"
              onClick={handleLogout}
              disabled={isLoggingOut}
            >
              <HiOutlineArrowLeftStartOnRectangle className="text-xl transition-transform duration-200 group-hover:scale-110" />
              <span className="text-base">
                {isLoggingOut ? navbar?.auth?.loggingOut || "Logging out..." : navbar?.auth?.logout}
              </span>
            </button>
          ) : null}
          {/* ccc<button onClick={handleLogout} className="capitalize cursor-pointer border rounded-4xl border-gray-800 text-red-700 px-4 py-0.5">{navbar?.auth?.logout}</button>} */}
        </div>
      </div>

      <div className="bg-black flex md:hidden p-5">
        <button
          onClick={toggleMenu}
          aria-label={navbar.menuToggle || "Toggle menu"}
          aria-expanded={isMenuOpen}
          className="relative block lg:hidden text-2xl z-30"
        >
          {isMenuOpen ? <IoClose /> : <IoMenu />}
        </button>
        <div
          className={`lg:hidden absolute top-0 left-0 right-0 bg-foreground p-5 shadow-md z-20 transform transition-all duration-300 ease-in-out
          ${
            isMenuOpen
              ? "opacity-100 visible translate-x-0"
              : "opacity-0 invisible translate-x-4"
          }
        `}
        >
          <ul className="flex flex-col items-center gap-4 py-4 text-primary text-lg">
            {filteredNavLinks.map((item) => {
              const normalizedUrl = normalizeUrl(item.url);
              if (item.protected) {
                if (isLoggedIn) {
                  return (
                    <li key={item.name}>
                      <Link href={normalizedUrl} onClick={() => setIsMenuOpen(false)}>
                        {item.name}
                      </Link>
                    </li>
                  );
                }
                return null;
              }
              return (
                <li key={item.name}>
                  <Link href={normalizedUrl} onClick={() => setIsMenuOpen(false)}>
                    {item.name}
                  </Link>
                </li>
              );
            })}
          </ul>
          <div className="flex items-center justify-center  my-3">
            {isLoggedIn && authState.accountType === "passenger" ? (
              <PassengerAccountMenu
                locale={locale}
                trans={{
                  logout: navbar?.auth?.logout || "Logout",
                  profile: navbar?.auth?.profile || "Profile",
                  logoutConfirmTitle: navbar?.auth?.logoutConfirmTitle || "Confirm Logout",
                  logoutConfirmMessage: navbar?.auth?.logoutConfirmMessage || "Are you sure you want to logout?",
                  confirm: navbar?.auth?.confirm || "Confirm",
                  cancel: navbar?.auth?.cancel || "Cancel",
                }}
              />
            ) : isLoggedIn ? (
              <button
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="group flex items-center justify-center gap-3 px-5 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg border border-red-500/30 hover:border-red-500/50 transition-all duration-200 font-medium disabled:opacity-50"
              >
                {isLoggingOut ? "Logging out..." : navbar?.auth?.logout}
              </button>
            ) : (
              <Link
                href={`/${locale}/auth`}
                onClick={(e) => {
                  handleLoginClick(e);
                  setIsMenuOpen(false);
                }}
                className="group flex items-center justify-center gap-3 px-5 py-2 bg-primary/10 hover:bg-primary/20 text-primary hover:text-primary/80 rounded-lg border border-primary/30 hover:border-primary/50 transition-all duration-200 font-medium"
              >
                {navbar?.auth?.login}
              </Link>
            )}
          </div>
          <div className="w-fit  mx-auto ">
            <SelectLanguage locale={locale} language={navbar.languages} />
          </div>
        </div>
        <Link href={`/${locale}`} className="block w-full">
          {" "}
          <div className="relative w-full h-[70px] md:me-auto">
            <Image
              src="/images/logo-witn-text.png"
              alt="landing_image"
              fill
              className="object-contain"
              quality={100}
              priority
            />
          </div>
        </Link>
      </div>
    </div>
  );
}
