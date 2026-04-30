import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import DashboardOverview from '@/components/_components/dashboard/DashboardOverview'


export default async function DashboardDashboardPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  const { dashboard } = await getTrans(locale, "dashboard") 
  const token = (await cookies()).get("userToken")?.value
  
  return (
    <div className='p-4 md:p-6 lg:p-8'>
     
      <DashboardOverview token={token} locale={locale} trans={dashboard} />
    </div>
  )
}