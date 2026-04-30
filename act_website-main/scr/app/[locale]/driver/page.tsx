import TripsDriver from '@/components/_components/driver/TripsDriver'
import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../i18n.config'
import getTrans from '@/lib/translation'
import { redirect } from 'next/navigation'

export default async function DriverPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale=(await params).locale
  const {myTrips}=await getTrans(locale,"driver")
  const token=(await cookies()).get("userToken")?.value

  // Check if driver is admin verified
  const cookieStore = await cookies();
  const isAdminVerified = cookieStore.get("is_admin_verified")?.value === "true";
  const accountType = cookieStore.get("account_type")?.value;

  // Redirect to home if driver is not verified or not a driver
  if (accountType !== "normal_driver" || !isAdminVerified) {
    redirect(`/${locale}`);
  }
  
  
  return (
    <div className=''><TripsDriver locale={locale} token={token} trans={myTrips}/></div>
  )
}
