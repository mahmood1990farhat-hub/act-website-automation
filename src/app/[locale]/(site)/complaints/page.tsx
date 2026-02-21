import Complaints from '@/components/_components/Complaints'
import getTrans from '@/lib/translation'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import { cookies } from 'next/headers'

export default async function ComplaintsPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale= (await params).locale

  const transComplaints = await getTrans(locale, "complaints")
  const token = (await cookies()).get("userToken")?.value
  
  
  return (
    <div className='min-h-screen bg-gradient py-8 md:py-12'>
      <div className='container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl'>
        <Complaints trans={transComplaints} token={token} locale={locale} />
      </div>
    </div>
  )
}

