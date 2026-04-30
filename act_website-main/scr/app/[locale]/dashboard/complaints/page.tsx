import { cookies } from "next/headers";
import React from "react";
import { Locale } from "../../../../../i18n.config";
import getTrans from "@/lib/translation";
import Complaints from "@/components/_components/dashboard/Complaints";

export default async function DashboardComplaintsPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const locale = (await params).locale;
  const complaintsTrans = await getTrans(locale, "complaints");
  const token = (await cookies()).get("userToken")?.value;

  return (
    <div className="py-4">
      <Complaints locale={locale} token={token} trans={complaintsTrans} />
    </div>
  );
}



