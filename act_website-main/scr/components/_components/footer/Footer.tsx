import Image from "next/image";
import React from "react";
import { FaFacebookF, FaInstagram, FaLinkedinIn, FaWhatsapp } from "react-icons/fa";
import { FaXTwitter } from "react-icons/fa6";
import Policy from "../Policy";
import Terms from "../Terms";
import Faqs from "../Faqs";
import Link from "next/link";
import { languageType, Locale } from "../../../../i18n.config";

type typeProps = {
  faqs :any ,terms:any ,privacyPolicy:any
  locale?: languageType;
  footer: {
    Our_Company: {
      title: string;
      Elements: {
        name: string;
        href: string;
      }[];
    };
    Call_us: {
      title: string;
      phone_numbers: { title: string; Elements: string[] };
      Email_us: { title: string; Elements: string[] };
      address: {
        postal_code: string;
        country: string;
      };
    };
    Policies: {
      title: string;
      Elements: {
        name: string;
        href: string;
      }[];
    };
    location: {
      title: string;
      Elements: string[];
    };
    logoAlt?: string;
    registeredCompany?: string;
    copyright?: string;
  };
};

export default function Footer({ footer ,faqs ,terms ,privacyPolicy, locale = "en" as languageType }: typeProps) {




  return (
    <footer className="lg:px-25 md:px-15 px-5 flex items-center justify-center flex-col gap-7 bg-black pt-15 pb-1 text-muted" id="footer">
      {/* section 1 */}
      <div className="md:flex items-start md:justify-between  grid gap-4 max-sm:gap-12 grid-cols-1 w-full text-center">
        {/* Our Company */}
        <div className="">
          <h1 className="font-bold text-white">{footer.Our_Company.title}</h1>
          <ul className="flex flex-col text-muted text-sm gap-3 mt-5">
            {footer.Our_Company.Elements.map((item) => {
              // Fix /apps links to go to /download-app with locale
              let href = item.href;
              if (item.href === "/apps" || item.href === "/download-app") {
                href = `/${locale}/download-app`;
              } else if (item.href === "/en" || item.href === "/ar") {
                // Normalize home links to current locale
                href = `/${locale}`;
              } else {
                // Replace any locale prefix with current locale
                href = item.href.replace(/^\/(en|ar)/, `/${locale}`);
              }
              return (
                <Link key={item.href} href={href} className="cursor-pointer hover:text-gray-400">{item.name}</Link>
              );
            })}
          </ul>
        </div>
        {/* Call_us */}
        <div className=" space-y-4">
          <h1 className="font-bold text-white capitalize">{footer.Call_us.title}</h1>
          <div>
            {/* <h3>{footer.Call_us.phone_numbers.title}</h3> */}
            <ul className="text-muted text-sm space-y-3 mt-2 p-1">
              {footer.Call_us.phone_numbers.Elements.map((item) => (
                <li key={item} dir="ltr">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div>
            {/* <h3>{footer.Call_us.Email_us.title}</h3> */}
            <ul className="text-muted text-sm space-y-3 mt-2 px-1 ">
              {footer.Call_us.Email_us.Elements.map((item) => (
                <li key={item} dir="ltr">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
        {/* park code */}
        {/* <div className="max-lg:hidden">
          {" "}
          <div className="relative w-[200px] h-[250px]   me-auto ">
            <Image
              src="/images/park-code.png"
              alt="landing_image"
              fill
              className="object-contain "
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
              quality={100}
              priority
            />
          </div>
        </div> */}
        {/*  */}
        <div className="">
          <h1 className="font-bold text-white">{footer.Policies.title}</h1>
          <ul className="text-muted text-sm space-y-3 mt-5">
            <li><Policy trans={privacyPolicy} locale={locale}/></li>
            <li><Terms trans={terms} locale={locale}/></li>
            <li><Faqs trans={faqs} locale={locale}/></li>
            {footer.Policies.Elements.map((item) => {
              // Fix /apps links to go to /download-app with locale
              const href = item.href === "/apps" || item.href === "/download-app" 
                ? `/${locale}/download-app` 
                : item.href;
              return (
                <Link key={item.href} href={href} className="cursor-pointer hover:text-gray-400">{item.name}</Link>
              );
            })}
          </ul>
        </div>
        {/*  */}
        <div className="max-md:mx-auto">
          <h1 className="font-bold text-white">{footer.location.title}</h1>
          <ul className="text-muted text-sm space-y-3 mt-5">
            {footer.location.Elements.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
      {/* <div className="lg:hidden rounded-xl overflow-hidden">
        <div className="relative w-[200px] h-[250px] me-auto rounded-xl overflow-hidden">
          <Image
            src="/images/park-code.png"
            alt="landing_image"
            fill
            className="object-contain rounded-xl overflow-hidden"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
            quality={100}
            priority
          />
        </div>
      </div> */}
      {/* section 2  */}
      <div className="flex items-center md:justify-between justify-center  w-full">
        <div className="lg:w-1/2 flex max-md:items-center flex-col space-y-4">
          <div className="flex items-center gap-9 text-black text-3xl">
            {" "}
            <FaFacebookF className="bg-primary p-1 rounded cursor-pointer" />
            <FaInstagram className="bg-primary p-1 rounded cursor-pointer" />
            <FaXTwitter className="bg-primary  p-1 rounded cursor-pointer" />
            <FaLinkedinIn className="bg-primary p-1 rounded cursor-pointer" />
            <Link href={'https://wa.me/message/VJH5RVGO3E2CH1'} target="_blank">
              <FaWhatsapp className="bg-primary p-1 rounded cursor-pointer" />
            </Link>
          </div>
          {/* <div className="md:w-1/2 max-md:text-center">
            Farhat Trading Solution Ltd, Airport House, Office 106, Purley Way,
            London, CR0 0XZ
          </div> */}
        </div>
        <div className="max-sm:hidden   ">
          {" "}
          <div className="relative lg:w-[350px] w-[200px] h-[190px]    ">
            <Image
              src="/images/logo-witn-text.png"
              alt={footer.logoAlt || "Logo"}
              fill
              className="object-contain "
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 1000px"
              quality={100}
              priority
            />
          </div>
        </div>
      </div>
      {/* section 3 */}
      <div className="w-full flex items-center justify-center flex-col gap-2.5 text-center  pb-4">
        <h1 className="text-primary font-semibold italic w-fit text-sm">
          {footer.registeredCompany || "Registered Company: Farhat Trading Solutions Ltd"}
        </h1>
        <h2 className="text-xs">
          {(footer.copyright || "All Copyright © {year} Airport taxi Transfer Company").replace(
            "{year}",
            String(new Date().getFullYear())
          )}
        </h2>
      </div>
    </footer>
  );
}
