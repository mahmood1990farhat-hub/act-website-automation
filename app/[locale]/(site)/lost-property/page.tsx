import LostProperty from '@/components/_components/LostProperty'
import getTrans from '@/lib/translation'
import React from 'react'
import { Locale } from '../../../../../i18n.config'
import { cookies } from 'next/headers'

export default async function LostPropertyPage({params}:{params:Promise<{locale:Locale}>}) {
  const locale= (await params).locale

  const transLostProperty = await getTrans(locale, "lostProperty")
  const token = (await cookies()).get("userToken")?.value
  
  
  return (
    <div className='min-h-screen bg-gradient py-8 md:py-12'>
      <div className='container mx-auto px-4 md:px-6 lg:px-8 max-w-7xl'>
        <LostProperty trans={transLostProperty} token={token} locale={locale} />
      </div>
    </div>
  )
}

