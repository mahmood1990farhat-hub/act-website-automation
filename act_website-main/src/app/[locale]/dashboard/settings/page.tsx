import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import PricingSettings from '@/components/_components/dashboard/PricingSettings'


export default async function DashboardSettingsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  const { dashboard } = await getTrans(locale, "dashboard") 
  const token = (await cookies()).get("userToken")?.value
  
  return (
    <div className='p-6'>
      <PricingSettings locale={locale} token={token} trans={dashboard} />
    </div>
  )
}