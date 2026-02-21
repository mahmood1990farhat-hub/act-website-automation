import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'
import EarningsWrapper from '@/components/_components/dashboard/EarningsWrapper'

export default async function DashboardEarningsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  const { dashboard } = await getTrans(locale, "dashboard") 
  const token = (await cookies()).get("userToken")?.value
  
  return (
    <div className='p-4 md:p-6 max-w-full overflow-x-hidden'>
      <EarningsWrapper locale={locale} token={token} trans={dashboard} />
    </div>
  )
}
