"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useEffect, useRef, useState } from "react";

import { TbWorld } from "react-icons/tb";

const languagew = [
  { name: "English", loacle: "en" },
  { name: "Arabic", loacle: "ar" },
];

function SelectLanguage({
  locale,
  language,
}: {
  locale: string;
  language: {
    English: string;
    Arabic: string;
  };
}) {
  const pathname = usePathname();
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [isOpen, setIsOpen] = useState(false);
  const [newPathname, setNewPathname] = useState("en");
  useEffect(() => {
    setNewPathname(
      pathname.replace(`/${locale}`, `/${locale !== "ar" ? "ar" : "en"}`)
    );
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);
  return (
    <div
      ref={dropdownRef}
      className=" relative cursor-pointer text-[16px]  border-muted rounded w-full text-gray-200"
      onClick={() => setIsOpen(!isOpen)}
    >
      <div
        className={`flex items-center  max-sm:justify-between gap-1.5 p-2  lg:px-3  sm:w-fit rounded-lg duration-300  `}
      >
        <TbWorld className="text-xl text-gray-200" />
        <h1 className="text-base font-medium text-gray-200">
          {locale == "en" ? language.English : language.Arabic}
        </h1>
      </div>
      {isOpen && (
        <ul
          className={` absolute  mt-1 p-2 w-full z-10 text-[16px] font-medium  rounded space-y-2 bg-black text-center  `}
        >
          <li
            onClick={() => setIsOpen(false)}
            className="hover:bg-gray-50/10 rounded p-1"
          >
            {locale === "ar" ? (
              <Link href={newPathname}>{language.English}</Link>
            ) : (
              language.English
            )}
          </li>
          <li
            onClick={() => setIsOpen(false)}
            className="hover:bg-gray-50/10 rounded p-1"
          >
            {locale !== "ar" ? (
              <Link href={newPathname}>{language.Arabic}</Link>
            ) : (
              language.Arabic
            )}
          </li>
        </ul>
      )}
    </div>
  );
}

export default SelectLanguage;
