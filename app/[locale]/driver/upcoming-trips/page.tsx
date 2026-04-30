import TripsDriver from "@/components/_components/driver/TripsDriver";
import { cookies } from "next/headers";
import React from "react";
import { Locale } from "../../../../../i18n.config";
import getTrans from "@/lib/translation";
import UpcomingTrips from "@/components/_components/driver/UpcomingTrips";

import MyMap from "@/components/_components/driver/GetMyLocation";

export default async function UpcomingTripsPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const locale = (await params).locale;
  const { myTrips } = await getTrans(locale, "driver");
  const token = (await cookies()).get("userToken")?.value;

  return (
    <div className="">
      {/* <MyMap /> */}
      <UpcomingTrips locale={locale} token={token} trans={myTrips} />
    </div>
  );
}
