import React from "react";
import { Locale } from "../../../../../i18n.config";
import Auth from "@/components/_components/auth/Auth";
import getTrans from "@/lib/translation";

type typePrpos = {
  params: Promise<{ locale: Locale }>;
  searchParams:Promise<{captain?:string}>
};

export default async function Authpage({ params ,searchParams}: typePrpos) {
  const { locale } = await params;
  const { captain } = await searchParams;
  const auth = await getTrans(locale, "auth");

  return (
    <div>
      <Auth locale={locale} trans={auth} isCaptain={captain} />
    </div>
  );
}
