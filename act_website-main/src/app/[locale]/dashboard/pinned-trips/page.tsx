import { cookies } from 'next/headers'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import getTrans from '@/lib/translation'


export default async function DashboardPinnedTripsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale = (await params).locale
  const { dashboard } = await getTrans(locale, "dashboard") 
  const token = (await cookies()).get("userToken")?.value
  
  return (
    <div className=''>
  
    </div>
  )
}