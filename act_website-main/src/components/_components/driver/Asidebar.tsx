"use client";
import { deleteCookie, getCookie } from "cookies-next";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import React, { useState, useEffect } from "react";
import { FaTimes } from "react-icons/fa";
import { FaCarOn, FaMapLocationDot, FaBars } from "react-icons/fa6";
import { IoMdCheckboxOutline } from "react-icons/io";
import { MdHail, MdMarkunreadMailbox } from "react-icons/md";
import { RiSettingsFill } from "react-icons/ri";
import { HiOutlineArrowLeftStartOnRectangle } from "react-icons/hi2";

// Icons array matching the navigation items
const icons = [
  <FaCarOn key="my-trips" />,
  <MdHail key="new-requests" />,
  <IoMdCheckboxOutline key="acceptable-trips" />,
  <FaMapLocationDot key="upcoming-trips" />,
  <MdMarkunreadMailbox key="monitor-trip" />,
  <RiSettingsFill key="settings" />,
];

export default function Asidebar({
  trans,
  adminVerification,
  sidebar,
}: {
  trans: { name: string; href: string }[];
  adminVerification?: { title: string; desc: string };
  sidebar?: {
    brandTitle?: string;
    logoAlt?: string;
    logout?: string;
    loggingOut?: string;
  };
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isAdminVerified, setIsAdminVerified] = useState<boolean | null>(null);
  
  // Extract locale from pathname (e.g., /en/driver/... or /ar/driver/...)
  const locale = pathname.split('/')[1] || 'en';
  
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
      setOpen(false);
      
      // Redirect to home page
      router.push(`/${locale}`);
      router.refresh();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setIsLoggingOut(false);
    }
  };

  // Check admin verification status on component mount
  useEffect(() => {
    const adminVerified = getCookie("is_admin_verified");
    setIsAdminVerified(adminVerified === "true");
  }, []);

  // Filter navigation items based on admin verification status
  const filteredTrans = isAdminVerified === false
    ? trans.filter((item, index) => index !== 0) // Remove "My Trips" (index 0) if not verified
    : trans;

  // Adjust icons array to match filtered navigation items
  const filteredIcons = isAdminVerified === false
    ? icons.slice(1) // Remove first icon (My Trips) if not verified
    : icons;

  return (
    <>
  
      <button
        className="md:hidden fixed w-full  z-50 flex items-center justify-between text-white bg-foreground p-5 rounded-b-lg "
        onClick={() => setOpen(!open)}
      >
        {open ? <FaTimes /> : <FaBars />}
               <h1 className="text-xl  font-bold   ">{sidebar?.brandTitle || "Airport City Group"}</h1>
          <div className="relative w-[20px] h-[20px] ">
          <Image src="/images/driver/logo_in_diver.png" alt={sidebar?.logoAlt || "logo"} fill />
        </div>
      </button>

      <aside
        className={`
          fixed top-0 left-0 h-full bg-foreground text-white text-center py-5 z-40 transition-transform duration-300
          ${open ? "translate-y-0  " : "max-md:-translate-y-full h-screen"}
          md:translate-x-0 md:relative md:flex
          w-full md:w-64 flex-col justify-between
        `}
      >
        <div className="flex items-center flex-col w-full">
          <h1 className="text-2xl w-1/2 font-bold mb-7 max-md:hidden  ">
            {sidebar?.brandTitle || "Airport City Group"}
          </h1>

          {/* Admin verification status notification */}
          {isAdminVerified === false && adminVerification && (
            <div className="w-full px-5 mb-4">
              <div className="bg-yellow-500/20 border border-yellow-500/30 rounded-lg p-3 text-center">
                <div className="text-yellow-400 text-sm font-medium mb-1">
                  ⏳ {adminVerification.title}
                </div>
                <div className="text-yellow-200 text-xs">
                  {adminVerification.desc}
                </div>
              </div>
            </div>
          )}

          <div className="w-full px-5">
            <nav>
              <ul className="text-[18px] space-y-4 font-semibold max-md:pt-15">
                {filteredTrans.map((item, index) => (
                  <li key={index}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 p-2 px-4 rounded ${
                        pathname === item.href
                          ? "text-foreground bg-gray-100"
                          : ""
                      }`}
                      onClick={() => setOpen(false)}
                    >
                      {filteredIcons[index]}
                      {item.name}
                    </Link>
                  </li>
                ))}
                <button 
                  className="font-bold text-lg w-full flex items-center gap-3 px-4 cursor-pointer disabled:opacity-50" 
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                > 
                  <HiOutlineArrowLeftStartOnRectangle /> 
                  {isLoggingOut
                    ? sidebar?.loggingOut || "Logging out..."
                    : sidebar?.logout || "Logout"}
                </button>
              </ul>
            </nav>
          </div>
        </div>
        <div className="relative w-[100px] h-[100px] mx-auto mt-10">
          <Image src="/images/driver/logo_in_diver.png" alt={sidebar?.logoAlt || "logo"} fill />
        </div>
      </aside>
    </>
  );
}
