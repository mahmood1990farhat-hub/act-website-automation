import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import AllPassengersDashboard from '@/components/_components/dashboard/AllPassengersDashboard'


export default async function DashboardPassengersPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  const { dashboard } = await getTrans(locale, "dashboard") 
  const token = (await cookies()).get("userToken")?.value
  
  return (
    <div className=''>
    <AllPassengersDashboard locale={locale} token={token} trans={dashboard}/>
    </div>
  )
}

