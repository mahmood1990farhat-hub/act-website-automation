"use client";

import React, { useState } from "react";
import SelectLanguage from "../header/SelectLanguage";
import { Locale } from "../../../../i18n.config";
import { IoMenu, IoClose } from "react-icons/io5";
import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { usePathname } from "next/navigation";

type tpyeProps = {
  navbar: {
    navLinks: {
      name: string;
      url: string;
    }[];
    languages: {
      English: string;
      Arabic: string;
    };
  };
  locale: Locale;
};

export default function Navber({ navbar, locale }: tpyeProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const toggleMenu = () => {
    setIsMenuOpen((prev) => !prev);
  };
  const pathname=usePathname()
  const pathn=pathname.split("/").slice(-1)[0]
  

  return (
    <div className="relative">
      <div className="hidden md:flex   items-center justify-center px-2  gap-10 my-5">
        <nav className="" role="navigation">
          <ul
            className={`flex  items-center justify-center text-primary lg:text-lg ${
              locale === "ar" ? "lg:gap-10 md:gap-5" : "md:gap-5 "
            }`}
          >
            {navbar.navLinks.slice(0, 4).map((item) => (
              <li
                key={item.name}
                className={`${
                  item.url === "/ar" || item.url === "/en"
                    ? "border-b-2 border-primary font-bold"
                    : ""
                } cursor-pointer`}
              >
                {item.url === "about-us" ? (
                  <a>{item.name}</a>
                ) : (
                  <Link href={item.url}>{item.name}</Link>
                )}
              </li>
            ))}
          </ul>
        </nav>
        <Link href={`/${locale}/auth`}>Register </Link>

        <div className="w-fit  ">
          <SelectLanguage locale={locale} language={navbar.languages} />
        </div>
      </div>

      <div className=" flex md:hidden p-5">
        <button
          onClick={toggleMenu}
          aria-label="Toggle menu"
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
            {navbar.navLinks.map((item) => (
              <li key={item.name}>
                <Link href={item.url} onClick={() => setIsMenuOpen(false)}>
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-center  my-3">
            <Button className="">
              <Link href={`/${locale}/auth`} className="text-lg p-6  ">
                Register{" "}
              </Link>
            </Button>
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
