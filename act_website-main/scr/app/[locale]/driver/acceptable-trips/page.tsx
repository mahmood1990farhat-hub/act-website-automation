import TripsDriver from '@/components/_components/driver/TripsDriver'
import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import UpcomingTrips from '@/components/_components/driver/UpcomingTrips'
import AcceptableTrips from '@/components/_components/driver/AcceptableTrips'



export default async function AcceptableTripsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale=(await params).locale
  const {myTrips}=await getTrans(locale,"driver")
  const token=(await cookies()).get("userToken")?.value
  
  
  return (
    <div className=''>

      <AcceptableTrips locale={locale} token={token} trans={myTrips}/></div>
  )
}
