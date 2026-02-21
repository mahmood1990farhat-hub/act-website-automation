import TripsDriver from '@/components/_components/driver/TripsDriver'
import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import MonitorTrip from '@/components/_components/driver/MonitorTrip'

export default async function MonitorTripPage({params ,searchParams}:{params:Promise<{locale:Locale}>,searchParams:Promise<{trip:string}>}) {
  const locale=(await params).locale
  const {myTrips}=await getTrans(locale,"driver")
  const token=(await cookies()).get("userToken")?.value
  const {trip}=await searchParams
  
  
  
  return (
    < ><MonitorTrip locale={locale} token={token} trans={myTrips} trip={trip}/></>
  )
}
