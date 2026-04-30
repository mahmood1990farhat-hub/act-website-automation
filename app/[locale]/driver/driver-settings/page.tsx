
import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import DriverSettings from '@/components/_components/driver/DriverSettings'

export default async function DriverSettingsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale=(await params).locale
  const {myTrips}=await getTrans(locale,"driver")
  const token=(await cookies()).get("userToken")?.value
  
  
  return (
    <div className=''><DriverSettings locale={locale} token={token} trans={myTrips}/></div>
  )
}


